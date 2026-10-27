# ADR 0011: Rate limiting próprio, por IP, em janela fixa e em memória

- **Status:** Aceita
- **Data:** 2026-10-27

## Contexto

Sem autenticação, a única barreira contra um cliente em laço ou abusivo é limitar quantas requisições ele faz. O candidato natural era o `fastapi-limiter`, que foi avaliado na versão 0.2.0 (sobre `pyrate-limiter` 4.5.1) antes da decisão:

- **O limite saía global.** Do jeito que o README ensina (`Limiter(Rate(2, Duration.SECOND * 5))`), a `pyrate-limiter` usa um balde só para todas as chaves: duas requisições do cliente A bloquearam o cliente B. Isso foi reproduzido num teste isolado. Para ter um balde por cliente, seria preciso escrever uma `BucketFactory` própria, e cada balde registra vazamento numa thread de fundo.
- **O identificador padrão confia no `X-Forwarded-For`.** Sem um proxy confiável na frente, qualquer cliente burla o limite mandando um IP inventado a cada requisição.
- **O 429 sai sem `Retry-After`.**

## Decisão

- `FixedWindowRateLimiter` próprio (`api/rate_limit.py`): até `N` requisições por cliente a cada janela de `S` segundos (padrão 60 por minuto), com contadores em memória protegidos por lock, porque as rotas síncronas rodam num pool de threads.
- Aplicado como dependência do router de livros: as duas rotas dividem o mesmo limite por cliente, e requisições inválidas também contam.
- O cliente é o IP da conexão (`request.client.host`). O `X-Forwarded-For` é ignorado; atrás de um proxy, quem reescreve o IP é o servidor (`uvicorn --forwarded-allow-ips`).
- Acima do limite: 429 com `Retry-After` (segundos até a janela virar).
- Os contadores são descartados quando a janela vira, então a memória acompanha os clientes ativos.
- O relógio é injetável, para os testes avançarem o tempo sem dormir.

## Alternativas consideradas

- **Rate limiting fora da aplicação, num proxy reverso ou API gateway** (`limit_req` do nginx, middleware do Traefik): é onde ele costuma ficar em produção, porque lá vale para todos os workers e não ocupa código da aplicação. Não foi a escolha porque a API é entregue para rodar sozinha com `uv run`, sem proxy na frente; nessa forma, ou ela se protege, ou não há proteção. Num deploy com proxy, o limite da aplicação fica como segunda barreira, com um valor mais alto (`LIBRARY_RATE_LIMIT_REQUESTS`).
- **`fastapi-limiter` corrigido:** exigiria a `BucketFactory` por chave, o identificador sem `X-Forwarded-For` e o callback com `Retry-After`. Seria código nosso de tamanho parecido, sobre duas dependências e uma thread de fundo.
- **`slowapi`:** decorator por rota, que exige o parâmetro `request` em toda rota, e tipagem fraca para o mypy strict.
- **Janela deslizante ou token bucket:** mais justos na virada da janela (na janela fixa, o pior caso é o dobro do limite somando o fim de uma janela e o começo da outra). Para proteger contra laço e uso abusivo, a janela fixa basta.

## Consequências

- O limite vale por processo. Com vários workers, cada um conta o seu; um limite compartilhado exige um contador central (Redis).
- O limite reinicia quando a aplicação reinicia.
- Clientes atrás do mesmo NAT dividem o mesmo limite.
