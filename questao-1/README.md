# Questão 1 - API de biblioteca virtual

API para cadastrar e consultar livros (título, autor, data de publicação e resumo), com FastAPI e SQLite.

## Enunciado × status

| Requisito do enunciado | Status |
| --- | --- |
| Cadastro de livros com título, autor, data de publicação e resumo | `POST /books` |
| Consulta de livros por título ou autor | `GET /books?title=&author=`, paginado; com os dois filtros, o livro precisa casar com ambos |
| Implementação com Django, Flask ou FastAPI | FastAPI |
| Endpoints claros e bem documentados | OpenAPI em `/docs`, com descrição, exemplos e respostas de erro |
| Armazenamento em SQLite | repositório pronto e testado |
| Testes unitários dos endpoints | `tests/api/`, de ponta a ponta com SQLite real |

## Além do enunciado

O enunciado pede cadastro e busca. Os itens abaixo foram acrescentados de propósito. Num time, cada um passaria antes pelo produto; aqui, sem a quem perguntar, a escolha foi mostrar como seriam modelados e deixar cada um isolado, para sair sem tocar o resto.

- **Estado de publicação (`is_published`).** Editoras e bibliotecas pré-cadastram livros antes do lançamento, então a data de publicação pode estar no futuro e a pergunta "já saiu?" passa a fazer sentido. A resposta é derivada da data, nunca guardada, para não existir uma flag discordando dela. O "hoje" usado na comparação é o do fuso da biblioteca, porque em UTC um lançamento de 28/10 apareceria publicado às 21h de 27/10 em São Paulo. Para tirar: o value object, o serviço e o DTO de saída. ([ADR 0003](docs/adr/0003-datas-e-estado-de-publicacao.md))
- **Busca sem caixa e sem acento.** O enunciado pede consulta por título ou autor, mas o `LIKE` do SQLite não acha "José" buscando "jose" nem "Érico" buscando "érico". Em português, sem isso, boa parte dos nomes simplesmente não aparece. Para tirar: as duas colunas normalizadas e a função de normalização do repositório. ([ADR 0005](docs/adr/0005-busca-sem-caixa-e-sem-acento.md))
- **Paginação obrigatória.** Uma lista sem limite cresce junto com o acervo até a resposta ficar lenta ou cair. A resposta diz se há próxima página em vez de trazer o total, porque contar na busca por trecho percorreria a tabela de novo a cada página. ([ADR 0006](docs/adr/0006-contrato-http-paginado-e-validacao-na-borda.md))
- **Validação estrita na borda.** No modo padrão, o pydantic aceita o número `0` como data (vira 01/01/1970) e ignora campos desconhecidos, então o cliente acharia que definiu o `id`. Por isso a data só entra como `AAAA-MM-DD`, campo desconhecido é erro, os textos têm teto de tamanho e texto sem nenhuma letra ou número (só espaços ou caracteres invisíveis) é recusado. ([ADR 0002](docs/adr/0002-entidade-valida-com-identidade-propria.md) e [ADR 0006](docs/adr/0006-contrato-http-paginado-e-validacao-na-borda.md))
- **Rate limiting por IP.** O enunciado não pede autenticação, e a API roda sozinha com `uv run`, sem proxy na frente. Limitar requisições por cliente é a proteção mínima contra um cliente em laço. A biblioteca candidata (`fastapi-limiter`) foi testada e descartada: o limite saía global e confiava num cabeçalho que qualquer cliente forja. Para tirar: a dependência do router e o módulo do limitador. ([ADR 0007](docs/adr/0007-rate-limiting-proprio-em-memoria.md))
- **Camadas (DDD enxuto).** Para dois endpoints, rotas acessando o banco direto bastariam. As camadas existem para que as regras sejam testadas sem banco nem servidor e para que cada item desta lista saia sem mexer nos outros. ([ADR 0001](docs/adr/0001-ddd-enxuto-em-camadas.md))

Interpretação do enunciado, não acréscimo: o **resumo é obrigatório**, porque o enunciado o lista junto dos outros campos sem marcá-lo como opcional.

## Como rodar

Pré-requisito: [uv](https://docs.astral.sh/uv/). O uv baixa o Python 3.12 sozinho se ele não estiver instalado.

```bash
uv sync
```

Subir a API (em `http://127.0.0.1:8000`, documentação interativa em `/docs`):

```bash
uv run library
```

Exemplos (o texto vai sem acento de propósito: no terminal do Windows, acento escrito direto na linha de comando chega ao `curl` fora de UTF-8 e o corpo vira JSON inválido; para testar com acentos, use o `/docs`):

```bash
curl -X POST http://127.0.0.1:8000/books -H "Content-Type: application/json" -d '{"title": "Dom Casmurro", "author": "Machado de Assis", "publication_date": "1899-01-01", "summary": "Bentinho narra o ciume que sente de Capitu."}'
```

```bash
curl "http://127.0.0.1:8000/books?author=machado&limit=20&offset=0"
```

A busca devolve uma página. Cada item tem o mesmo formato do livro que o cadastro devolve no 201; `has_more` diz se há próxima página, que se pede com `offset` igual a `offset + limit`:

```json
{
  "items": [
    {
      "id": "3c9bd357-6195-43ab-a2b3-c8b75e5f0580",
      "title": "Dom Casmurro",
      "author": "Machado de Assis",
      "summary": "Bentinho narra o ciume que sente de Capitu.",
      "publication_date": "1899-01-01",
      "is_published": true,
      "created_at": "2026-10-28T10:57:56.015591Z"
    }
  ],
  "limit": 20,
  "offset": 0,
  "has_more": false
}
```

Dado inválido volta como 422, sempre no mesmo formato, venha o erro do schema (campo vazio, data fora do formato) ou de uma regra do livro (título só com espaços), com o campo em `loc`:

```json
{
  "detail": [
    {"type": "domain_error", "loc": ["body", "title"], "msg": "title precisa ter pelo menos uma letra ou número"}
  ]
}
```

Acima do limite de requisições, a resposta é 429 com o cabeçalho `Retry-After`.

Configuração por variável de ambiente. Todas são opcionais; sem nenhuma, valem os padrões e `uv run library` basta. Para mudar algum valor, copie o [`.env.example`](.env.example) para `.env` (que fica fora do git) e rode com o arquivo:

```bash
uv run --env-file .env library
```

| Variável | Padrão | Para que serve |
| --- | --- | --- |
| `LIBRARY_DATABASE_PATH` | `library.db` | arquivo do SQLite |
| `LIBRARY_TIMEZONE` | `America/Sao_Paulo` | fuso da biblioteca, que define o "hoje" de `is_published` |
| `LIBRARY_RATE_LIMIT_REQUESTS` | `60` | requisições permitidas por cliente a cada janela |
| `LIBRARY_RATE_LIMIT_WINDOW_SECONDS` | `60` | tamanho da janela do rate limiting |

Validação de estilo e de tipos:

```bash
uv run ruff check .
```

```bash
uv run ruff format --check .
```

```bash
uv run mypy
```

Testes:

```bash
uv run pytest
```

## Estrutura

```
src/library/
├── domain/
│   ├── book.py                      entidade Book e suas invariantes
│   ├── publication_date.py          value object PublicationDate
│   ├── repository.py                porta BookRepository (o que o domínio precisa do banco)
│   ├── clock.py                     política de tempo (UTC)
│   └── errors.py                    erros de domínio
├── infrastructure/
│   ├── database.py                  conexão e schema do SQLite
│   └── sqlite_book_repository.py    SqliteBookRepository, implementação da porta
├── application/
│   ├── book_service.py              casos de uso (cadastrar, buscar) e o "hoje" da biblioteca
│   └── dtos.py                      comando de entrada, BookDTO e BookPage
└── api/
    ├── app.py                       create_app, lifespan e erros de domínio → HTTP
    ├── routes.py                    POST /books e GET /books
    ├── schemas.py                   contrato HTTP (pydantic) e validação da borda
    ├── dependencies.py              conexão por requisição, BookService e rate limiting
    ├── rate_limit.py                FixedWindowRateLimiter
    ├── settings.py                  configuração por variável de ambiente
    └── main.py                      ponto de entrada (uv run library)
tests/
├── conftest.py                      fixture make_book, compartilhada entre as suítes
├── domain/                          testes unitários do domínio
├── infrastructure/                  testes do repositório contra SQLite real
├── application/                     testes do BookService (o "hoje" da biblioteca)
└── api/                             testes HTTP dos endpoints e do rate limiter
docs/
├── adr/                             decisões de arquitetura desta questão
└── qualidade.md                     cobertura dos testes, regras quebradas de propósito e bugs registrados
```

As dependências apontam para dentro: `api` → `application` → `domain` ← `infrastructure` ([ADR 0001](docs/adr/0001-ddd-enxuto-em-camadas.md)). As rotas só conhecem a aplicação; o ponto de montagem da API (`app.py` e `dependencies.py`) é o único que importa a infraestrutura, para ligar o `BookService` ao SQLite, e os erros do domínio, para traduzi-los em HTTP.

## Decisões

O porquê de cada decisão, com as alternativas descartadas, está nas [ADRs desta questão](docs/adr/README.md). As que valem para o repositório inteiro (um projeto uv por questão, Python 3.12) e as convenções (idioma, ruff, mypy) estão no [README da raiz](../README.md).

1. [DDD enxuto, em camadas, com a aplicação como única porta da API](docs/adr/0001-ddd-enxuto-em-camadas.md)
2. [Entidade válida por construção, com identidade própria](docs/adr/0002-entidade-valida-com-identidade-propria.md)
3. [Instantes em UTC, data de publicação como dia, publicação derivada](docs/adr/0003-datas-e-estado-de-publicacao.md)
4. [Persistência com `sqlite3` da stdlib, num repositório único](docs/adr/0004-persistencia-sqlite3-com-repositorio-unico.md)
5. [Busca parcial, sem diferenciar maiúsculas nem acentos](docs/adr/0005-busca-sem-caixa-e-sem-acento.md)
6. [Contrato HTTP com paginação obrigatória e validação estrita na borda](docs/adr/0006-contrato-http-paginado-e-validacao-na-borda.md)
7. [Rate limiting próprio, por IP, em janela fixa e em memória](docs/adr/0007-rate-limiting-proprio-em-memoria.md)

O que destas decisões vai além do enunciado, e por quê, está em [Além do enunciado](#além-do-enunciado).

## Testes

A suíte cobre as quatro camadas: domínio, repositório contra SQLite real, aplicação e API de ponta a ponta. Cada teste protege uma regra de negócio ou um caso de borda e diz, num comentário, que estrago evita; cada regra foi quebrada de propósito para conferir que a suíte falha; todo bug encontrado virou um teste antes da correção.

O que cada suíte cobre, as regras quebradas de propósito, o que ficou de fora e os bugs registrados estão em [`docs/qualidade.md`](docs/qualidade.md).
