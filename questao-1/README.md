# Questão 1 - API de biblioteca virtual

API para cadastrar e consultar livros (título, autor, data de publicação e resumo), com FastAPI e SQLite.

## Enunciado × status

| Requisito do enunciado | Status |
| --- | --- |
| Cadastro de livros com título, autor, data de publicação e resumo | `POST /books` |
| Consulta de livros por título ou autor | `GET /books?title=&author=`, paginado |
| Implementação com Django, Flask ou FastAPI | FastAPI |
| Endpoints claros e bem documentados | OpenAPI em `/docs`, com descrição, exemplos e respostas de erro |
| Armazenamento em SQLite | repositório pronto e testado |
| Testes unitários dos endpoints | `tests/api/`, de ponta a ponta com SQLite real |

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
docs/adr/                            decisões de arquitetura desta questão
```

As dependências apontam para dentro: `api` → `application` → `domain` ← `infrastructure` ([ADR 0001](docs/adr/0001-ddd-enxuto-em-camadas.md)). As rotas só conhecem a aplicação; o ponto de montagem da API (`app.py` e `dependencies.py`) é o único que importa a infraestrutura, para ligar o `BookService` ao SQLite, e os erros do domínio, para traduzi-los em HTTP.

## Decisões

Cada decisão de arquitetura tem uma ADR com contexto, alternativas descartadas e consequências. Aqui fica só o resumo.

### Do repositório ([`../docs/adr/`](../docs/adr/README.md))

- **Um repositório, um projeto uv por questão.** As dependências das questões não se sobrepõem, e a questão 3 traz o torch. Uv workspace descartado por acoplar versões sem ganho. [ADR 0001](../docs/adr/0001-monorepo-com-projeto-uv-por-questao.md)
- **Python 3.12.** Versão mais segura para as wheels de FAISS e torch da questão 3, igual nas três questões. [ADR 0002](../docs/adr/0002-python-3-12.md)
- **Código em inglês, documentação em português.** Sem misturar idiomas dentro do código. [ADR 0003](../docs/adr/0003-codigo-em-ingles-documentacao-em-portugues.md)
- **ruff (120 colunas, regras enxutas) e mypy strict sobre `src/` e `tests/`, com layout `src`.** [ADR 0004](../docs/adr/0004-qualidade-ruff-e-mypy-strict.md)

### Desta questão ([`docs/adr/`](docs/adr/README.md))

- **DDD enxuto.** Camadas com dependências apontando para dentro; o domínio não conhece banco nem framework. Value object só onde há regra a proteger, sem agregados ou eventos enquanto o domínio for uma entidade e duas operações. [ADR 0001](docs/adr/0001-ddd-enxuto-em-camadas.md)
- **Instantes em UTC, datas de calendário sem fuso.** `created_at` é UTC no domínio e no banco; a data de publicação é `date` e não muda de dia conforme o fuso de quem consulta. A API devolve instantes em UTC; converter para o fuso do cliente seria papel da borda, e não foi implementado. [ADR 0002](docs/adr/0002-instantes-em-utc-datas-sem-fuso.md)
- **Identidade por UUID gerado no domínio.** O livro nasce com `id`, sem `id: int | None`, e se compara só pelo `id`. [ADR 0003](docs/adr/0003-identidade-por-uuid-do-dominio.md)
- **Entidade válida por construção.** Invariantes no `__post_init__`, erros de domínio próprios. Regra que vem do negócio fica no domínio; proteção técnica, como limite de tamanho dos textos, fica no schema da API. [ADR 0004](docs/adr/0004-entidade-valida-por-construcao.md)
- **`PublicationDate` como fonte única do estado de publicação.** Aceita data futura (pré-cadastro) e deriva `is_published(as_of)` em vez de guardar uma flag; o dia de referência vem de quem chama. [ADR 0005](docs/adr/0005-publication-date-como-fonte-unica.md)
- **Testes protegem regras de negócio; todo bug vira teste.** [ADR 0006](docs/adr/0006-testes-protegem-regras-de-negocio.md)
- **Persistência com `sqlite3` da stdlib, num repositório único.** Porta no domínio, implementação na infraestrutura, SQL explícito e sem ORM. Leitura e escrita no mesmo repositório: CQRS seria exagero para um endpoint de cada. Tabela `STRICT` com `CHECK`s que repetem a política de datas no banco. [ADR 0007](docs/adr/0007-persistencia-sqlite3-com-repositorio-unico.md)
- **Busca parcial, sem diferenciar maiúsculas nem acentos.** "jose" acha "José de Alencar"; `%` e `_` digitados são texto, não curinga. [ADR 0008](docs/adr/0008-busca-sem-caixa-e-sem-acento.md)
- **Camada de aplicação como única porta da API.** `BookService` recebe o repositório pela porta do domínio e devolve DTOs; a entidade nunca sai da aplicação. `is_published` é calculado no "hoje" do fuso da biblioteca. [ADR 0009](docs/adr/0009-camada-de-aplicacao-com-dtos.md)
- **Contrato HTTP com paginação obrigatória e validação estrita na borda.** `limit` (até 100) e `offset` (até 1 milhão) com `has_more`; data só como `AAAA-MM-DD`; campo desconhecido é erro; tetos de tamanho dos textos; 422 num formato só, venha o erro do schema ou do domínio. Sem autenticação, porque o enunciado não pede; isso pressupõe uso em ambiente controlado. [ADR 0010](docs/adr/0010-contrato-http-e-validacao-na-borda.md)
- **Proteção básica por rate limiting.** Limite simples por IP, com 429 e `Retry-After`, porque a API roda sem proxy na frente. [ADR 0011](docs/adr/0011-rate-limiting-proprio-em-memoria.md)

Decisão de produto, fora das ADRs: o **resumo é obrigatório**, porque o enunciado o lista junto dos outros campos sem marcá-lo como opcional.

## Testes

O que cada suíte cobre:

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

**Os testes protegem de verdade:** é necessário garantir que um teste fica vermelho se sua regra for quebrada, seguindo os padrões de RED -> GREEN. Cada regra foi quebrada de propósito, uma por vez, e em todas a suíte falhou:

- **Domínio:** trocar `<=` por `<` no `is_published`, tirar o `strip`, tirar a checagem de offset, trocar `utc_now()` por `datetime.now()`, desligar a igualdade por `id`, aceitar `datetime` como data de publicação, pular a conversão do `created_at`.
- **Repositório:** tirar o commit, trocar por `INSERT OR REPLACE`, não escapar `%`, buscar sem normalizar, ordenar pela coluna original, tirar o desempate por `id`, gravar `created_at` sem largura fixa, combinar filtros com OU, recriar a tabela no `create_schema`, tirar o `CHECK` de UTC, e trocar a chave primária por um "já existe?" antes do insert (check-then-act). Este último depende de corrida entre threads, então foi rodado 20 vezes: a suíte falhou nas 20. Na paginação: tirar a barreira de `limit`/`offset`, aceitar `limit` zero, trocar `LIMIT` e `OFFSET` de lugar, ignorar o `OFFSET`.
- **Aplicação:** ignorar o "hoje" injetado no cadastro e na busca, tirar o fuso do `today_in`, calcular um "hoje" por livro em vez de um por página.
- **API:** limiter com `>` no lugar de `>=`, sem reset de janela, com contador global e identificando o cliente pelo `X-Forwarded-For`; data sem a validação estrita; campos extras ignorados; `limit` máximo de 1000 e padrão de 100; filtro em branco aceito; `has_more` com `>=`; busca sem a linha extra; `is_published` fixo; sem o handler de `DomainError`.

**Deixado de fora:**

- **Concorrência no rate limiter.** O teste com 64 threads disputando o mesmo contador passou com e sem o lock nas 10 rodadas: com o GIL do CPython, a corrida entre ler e gravar o contador quase nunca acontece num trecho tão curto. Um teste que não falha com a regra quebrada não protege nada, então saiu. O lock continua no código, porque a corrida existe.
- **409 pela API.** O `id` é gerado no domínio, então nenhum corpo de requisição produz um livro duplicado, e o 409 fica fora do contrato. O caso está coberto no repositório (`BookAlreadyExistsError`).
- **Teste de N+1.** A busca é uma consulta só, e a reidratação do `Book` não consulta o banco; com uma tabela e nenhuma relação, não existe N+1 possível. O teste entra junto com a primeira relação (autor como tabela própria, por exemplo), contando as consultas com `connection.set_trace_callback`.

### Bugs registrados

Todo bug vira um teste que o reproduz antes da correção ([ADR 0006](docs/adr/0006-testes-protegem-regras-de-negocio.md)).

**1. Texto só com caractere invisível era aceito**

- **Bug:** título, autor ou resumo só com espaço de largura zero (U+200B) ou BOM (U+FEFF) passava pela validação, e o livro entrava com título invisível. Com o caractere nas pontas, "Machado de Assis" e "Machado de Assis" + U+200B viravam autores diferentes na busca.
- **Como apareceu:** escrevendo a suíte do domínio. O `str.strip()` só remove o que o Python considera espaço, e esses caracteres são da categoria Unicode "Cf" (formatação). Chegam colados de sites, PDFs e planilhas.
- **Testes que o protegem:** `test_rejects_blank_required_text` (casos `largura-zero`, `bom` e `misturado`) e `test_strips_invisible_characters_from_the_edges`.
- **Correção:** `_strip_invisible`, em `book.py`, remove espaços e caracteres "Cf" só das pontas. No meio do texto eles ficam, porque lá compõem emojis e a escrita de idiomas como persa e hindi. `test_keeps_invisible_characters_inside_the_text` impede que a correção vá longe demais.

Os bugs 2 a 6 foram encontrados na revisão final da questão, por um revisor independente.

**2. A correção do bug 1 era incompleta**

- **Bug:** título só com caractere de controle (NUL), acento solto, braille em branco ou preenchedor hangul continuava sendo aceito: nenhum deles é espaço nem "Cf".
- **Testes que o protegem:** `test_rejects_text_without_any_letter_or_digit` e `test_keeps_real_text_and_strips_invisible_edges`.
- **Correção:** em vez de listar o que é invisível, o texto precisa ter pelo menos uma letra ou um número (categorias Unicode "L" e "N"). Os preenchedores hangul, que o Unicode classifica como letra, são tratados à parte, e caracteres de controle também saem das pontas.

**3. `offset` grande derrubava a busca com 500**

- **Bug:** `GET /books?offset=100000000000000000000` estourava o inteiro do sqlite3 (`OverflowError`) e respondia 500.
- **Teste:** `test_search_rejects_offset_beyond_the_ceiling`.
- **Correção:** teto de 1 milhão no `offset`.

**4. Configuração inválida só aparecia com a API no ar**

- **Bug:** `LIBRARY_RATE_LIMIT_WINDOW_SECONDS=0` fazia toda requisição dar 500 (divisão por zero), `LIBRARY_RATE_LIMIT_REQUESTS=0` bloqueava todo mundo com 429, e um fuso inválido derrubava a subida com um traceback sem o nome da variável.
- **Testes:** `test_settings.py`.
- **Correção:** o `Settings` valida os valores na construção, e o `from_env` nomeia a variável no erro.

**5. O 422 tinha dois formatos, e o contrato anunciava um 409 inalcançável**

- **Bug:** título vazio voltava como lista de erros (pydantic) e título só com espaços como texto (domínio). O OpenAPI do cadastro trazia o 422 sem schema e um 409 que nenhuma requisição produz.
- **Testes:** `test_validation_errors_have_one_shape_and_point_to_the_field` e `test_openapi_documents_only_the_errors_the_api_can_return`.
- **Correção:** o `DomainError` carrega o campo violado, e o handler devolve o mesmo formato do pydantic. O 409 continua como defesa, fora do contrato.

**6. A virada da janela do rate limiter podia zerar os contadores mais de uma vez**

- **Bug:** o relógio era lido fora do lock. Uma requisição atrasada da janela anterior que entrasse no lock depois de outra da janela nova fazia a janela "voltar" e zerava os contadores, e a requisição seguinte zerava de novo.
- **Teste:** `test_late_request_from_the_previous_window_does_not_reset_the_counters`, com um relógio que anda para trás para simular a ordem de chegada.
- **Correção:** o relógio é lido dentro do lock, e a janela só avança.
