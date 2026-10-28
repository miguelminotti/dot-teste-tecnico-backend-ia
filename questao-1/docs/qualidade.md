# Qualidade da questão 1: testes e bugs

Como a suíte é pensada, o que cada arquivo de teste protege, como foi conferido que os testes pegam regra quebrada e o registro dos bugs encontrados. Para rodar: `uv run pytest`, na pasta da questão.

## Política da suíte

- Cada teste protege uma regra de negócio ou um caso de borda conhecido, e um comentário dentro dele diz qual estrago ele evita. A mecânica da linguagem ou da biblioteca (imutabilidade da dataclass, `repr`) só é testada se sustenta uma regra. Meta de cobertura de linhas ficou de fora, porque incentiva teste que executa código sem verificar regra.
- Um teste só vale se fica vermelho quando sua regra é quebrada. Cada regra foi quebrada de propósito para confirmar (lista abaixo); as mutações foram feitas à mão, porque uma ferramenta como o mutmut é peso demais para este tamanho.
- Todo bug vira teste: primeiro um teste que o reproduz e falha, depois a correção. O bug fica registrado no fim deste documento.
- Fusos nos testes usam offset fixo, não `ZoneInfo`: o que está em teste é a conversão, não a base de fusos do sistema operacional.
- Caracteres invisíveis são escritos como sequências de escape (`"\N{ZERO WIDTH SPACE}"`), nunca literais, para quem lê ver o que está sendo testado.
- Helpers de teste ficam no arquivo que os usa e vão para o `conftest.py` quando um segundo arquivo precisa deles.

## O que cada suíte cobre

| Arquivo | Regras protegidas |
| --- | --- |
| `test_clock.py` | relógio sempre em UTC; conversão que vira o dia (22h em São Paulo, 8h em Tóquio); recusa de instante sem fuso, inclusive o fuso que existe mas não informa offset |
| `test_publication_date.py` | o dia do lançamento já conta como publicado; data futura aceita (pré-cadastro); recusa de `datetime` como data de publicação e como dia de referência |
| `test_book.py` | título, autor e resumo sem nenhuma letra ou número recusados (em branco, espaço não quebrável, caracteres invisíveis, de controle, acento solto, braille em branco, preenchedor hangul); espaços e invisíveis das pontas removidos, os do meio preservados; título só com números e acento combinado no fim aceitos; `created_at` sempre em UTC; identidade pelo `id` |
| `test_sqlite_book_repository.py` | cadastro sobrevive ao fechar a conexão (commit); ida e volta preserva todos os campos, inclusive data futura e horário de São Paulo; datas gravadas em UTC de largura fixa e dia puro; `id` duplicado vira erro de domínio sem sobrescrever o original; erro não deixa transação aberta; oito cadastros simultâneos do mesmo livro gravam um só; recriar o schema não apaga o acervo; banco recusa datas fora da política; busca sem caixa e acento, com `%`, `_` e `\` como texto, filtros combinados com E, ordem alfabética e desempate por `id`; paginação devolve a fatia certa do resultado ordenado e recusa `limit` menor que 1 e `offset` negativo (no SQLite, `LIMIT -1` é "sem limite") |
| `test_book_service.py` | `is_published` usa o "hoje" que o serviço recebe, não o relógio; o "hoje" da biblioteca converte o instante UTC para o dia do fuso (01h UTC de 28/10 ainda é 27/10 em São Paulo); todos os livros de uma página usam o mesmo dia, mesmo se a meia-noite passar no meio da montagem |
| `test_books_api.py` | cadastro devolve o livro com os campos do contrato e o grava de fato; `is_published` segue a data (pré-cadastro sai como não publicado); payload inválido é recusado com 422 e nada é gravado (data numérica, com hora, em outro formato ou inexistente; `id` ou `is_published` mandados pelo cliente; campo faltando ou nulo; texto acima do limite; texto em branco ou invisível); 422 num formato só, com o campo no `loc`, venha o erro do schema ou do domínio; OpenAPI do cadastro documenta só 201, 422 (com schema) e 429; busca por título e por autor sem caixa e acento; paginação devolve cada livro exatamente uma vez, inclusive com total múltiplo do `limit`; página padrão de 20; parâmetros que anulariam a paginação recusados; `offset` acima do teto dá 422, não 500; 429 com `Retry-After`; `X-Forwarded-For` forjado não burla o limite |
| `test_rate_limit.py` | permite exatamente o limite e informa quanto falta para a janela virar; o limite reinicia na janela seguinte; requisição atrasada da janela anterior não zera os contadores; cada cliente tem o seu contador |
| `test_settings.py` | configuração que derrubaria ou bloquearia a API (janela zero ou negativa, zero requisições) é recusada na subida; variável inválida (não numérica, fuso inexistente) é nomeada no erro |

Os testes da infraestrutura e da API rodam contra SQLite real, sem fake: em memória quando basta uma conexão, num arquivo temporário quando precisam de mais de uma (persistência e concorrência) e um banco próprio por teste na API. Os testes da API sobem a aplicação com `create_app` e o `TestClient`, que executa o lifespan como na subida real.

## Regras quebradas de propósito

Uma por vez; em todas a suíte falhou.

- **Domínio:** trocar `<=` por `<` no `is_published`, tirar o `strip`, tirar a checagem de offset, trocar `utc_now()` por `datetime.now()`, desligar a igualdade por `id`, aceitar `datetime` como data de publicação, pular a conversão do `created_at`.
- **Repositório:** tirar o commit, trocar por `INSERT OR REPLACE`, não escapar `%`, buscar sem normalizar, ordenar pela coluna original, tirar o desempate por `id`, gravar `created_at` sem largura fixa, combinar filtros com OU, recriar a tabela no `create_schema`, tirar o `CHECK` de UTC, e trocar a chave primária por um "já existe?" antes do insert (check-then-act). Este último depende de corrida entre threads, então foi rodado 20 vezes: a suíte falhou nas 20. Na paginação: tirar a barreira de `limit`/`offset`, aceitar `limit` zero, trocar `LIMIT` e `OFFSET` de lugar, ignorar o `OFFSET`.
- **Aplicação:** ignorar o "hoje" injetado no cadastro e na busca, tirar o fuso do `today_in`, calcular um "hoje" por livro em vez de um por página.
- **API:** limiter com `>` no lugar de `>=`, sem reset de janela, com contador global e identificando o cliente pelo `X-Forwarded-For`; data sem a validação estrita; campos extras ignorados; `limit` máximo de 1000 e padrão de 100; filtro em branco aceito; `has_more` com `>=`; busca sem a linha extra; `is_published` fixo; sem o handler de `DomainError`.

## Deixado de fora

- **Concorrência no rate limiter.** O teste com 64 threads disputando o mesmo contador passou com e sem o lock nas 10 rodadas: com o GIL do CPython, a corrida entre ler e gravar o contador quase nunca acontece num trecho tão curto. Um teste que não falha com a regra quebrada não protege nada, então saiu. O lock continua no código, porque a corrida existe.
- **409 pela API.** O `id` é gerado no domínio, então nenhum corpo de requisição produz um livro duplicado, e o 409 fica fora do contrato. O caso está coberto no repositório (`BookAlreadyExistsError`).
- **Teste de N+1.** A busca é uma consulta só, e a reidratação do `Book` não consulta o banco; com uma tabela e nenhuma relação, não existe N+1 possível. O teste entra junto com a primeira relação (autor como tabela própria, por exemplo), contando as consultas com `connection.set_trace_callback`.

## Bugs registrados

Cada bug tem um teste que o reproduziu antes da correção.

### 1. Texto só com caractere invisível era aceito

- **Bug:** título, autor ou resumo só com espaço de largura zero (U+200B) ou BOM (U+FEFF) passava pela validação, e o livro entrava com título invisível. Com o caractere nas pontas, "Machado de Assis" e "Machado de Assis" + U+200B viravam autores diferentes na busca.
- **Como apareceu:** escrevendo a suíte do domínio. O `str.strip()` só remove o que o Python considera espaço, e esses caracteres são da categoria Unicode "Cf" (formatação). Chegam colados de sites, PDFs e planilhas.
- **Testes que o protegem:** `test_rejects_blank_required_text` (casos `largura-zero`, `bom` e `misturado`) e `test_strips_invisible_characters_from_the_edges`.
- **Correção:** `_strip_invisible`, em `book.py`, remove espaços e caracteres "Cf" só das pontas. No meio do texto eles ficam, porque lá compõem emojis e a escrita de idiomas como persa e hindi. `test_keeps_invisible_characters_inside_the_text` impede que a correção vá longe demais.

Os bugs 2 a 6 foram encontrados na revisão final da questão, por um revisor independente.

### 2. A correção do bug 1 era incompleta

- **Bug:** título só com caractere de controle (NUL), acento solto, braille em branco ou preenchedor hangul continuava sendo aceito: nenhum deles é espaço nem "Cf".
- **Testes que o protegem:** `test_rejects_text_without_any_letter_or_digit` e `test_keeps_real_text_and_strips_invisible_edges`.
- **Correção:** em vez de listar o que é invisível, o texto precisa ter pelo menos uma letra ou um número (categorias Unicode "L" e "N"). Os preenchedores hangul, que o Unicode classifica como letra, são tratados à parte, e caracteres de controle também saem das pontas.

### 3. `offset` grande derrubava a busca com 500

- **Bug:** `GET /books?offset=100000000000000000000` estourava o inteiro do sqlite3 (`OverflowError`) e respondia 500.
- **Teste:** `test_search_rejects_offset_beyond_the_ceiling`.
- **Correção:** teto de 1 milhão no `offset`.

### 4. Configuração inválida só aparecia com a API no ar

- **Bug:** `LIBRARY_RATE_LIMIT_WINDOW_SECONDS=0` fazia toda requisição dar 500 (divisão por zero), `LIBRARY_RATE_LIMIT_REQUESTS=0` bloqueava todo mundo com 429, e um fuso inválido derrubava a subida com um traceback sem o nome da variável.
- **Testes:** `test_settings.py`.
- **Correção:** o `Settings` valida os valores na construção, e o `from_env` nomeia a variável no erro.

### 5. O 422 tinha dois formatos, e o contrato anunciava um 409 inalcançável

- **Bug:** título vazio voltava como lista de erros (pydantic) e título só com espaços como texto (domínio). O OpenAPI do cadastro trazia o 422 sem schema e um 409 que nenhuma requisição produz.
- **Testes:** `test_validation_errors_have_one_shape_and_point_to_the_field` e `test_openapi_documents_only_the_errors_the_api_can_return`.
- **Correção:** o `DomainError` carrega o campo violado, e o handler devolve o mesmo formato do pydantic. O 409 continua como defesa, fora do contrato.

### 6. A virada da janela do rate limiter podia zerar os contadores mais de uma vez

- **Bug:** o relógio era lido fora do lock. Uma requisição atrasada da janela anterior que entrasse no lock depois de outra da janela nova fazia a janela "voltar" e zerava os contadores, e a requisição seguinte zerava de novo.
- **Teste:** `test_late_request_from_the_previous_window_does_not_reset_the_counters`, com um relógio que anda para trás para simular a ordem de chegada.
- **Correção:** o relógio é lido dentro do lock, e a janela só avança.
