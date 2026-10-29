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

Cada item fica isolado e sai sem mexer nos outros; o porquê está na ADR indicada.

- **`is_published`:** livro pode ser pré-cadastrado com data futura; o estado é derivado da data, no fuso da biblioteca ([ADR 0003](docs/adr/0003-datas-e-estado-de-publicacao.md)).
- **Busca sem caixa e sem acento:** "jose" acha "José", o que o `LIKE` do SQLite não faz ([ADR 0005](docs/adr/0005-busca-sem-caixa-e-sem-acento.md)).
- **Paginação obrigatória:** com `has_more` no lugar do total, que obrigaria a percorrer a tabela de novo ([ADR 0006](docs/adr/0006-contrato-http-paginado-e-validacao-na-borda.md)).
- **Validação estrita na borda:** data só como `AAAA-MM-DD`, campo ou parâmetro desconhecido é erro, texto sem letra nem número é recusado ([ADR 0002](docs/adr/0002-entidade-valida-com-identidade-propria.md) e [ADR 0006](docs/adr/0006-contrato-http-paginado-e-validacao-na-borda.md)).
- **Rate limiting por IP:** proteção mínima contra um cliente em laço, já que a API roda sem proxy na frente ([ADR 0007](docs/adr/0007-rate-limiting-proprio-em-memoria.md)).
- **Camadas (DDD enxuto):** para testar as regras sem banco nem servidor ([ADR 0001](docs/adr/0001-ddd-enxuto-em-camadas.md)).

O **resumo é obrigatório**, porque o enunciado o lista junto dos outros campos sem marcá-lo como opcional.

## Como rodar

Pré-requisito: [uv](https://docs.astral.sh/uv/), que baixa o Python 3.12 se ele não estiver instalado.

```bash
uv sync
```

```bash
uv run library
```

A API sobe em `http://127.0.0.1:8000`, com documentação interativa em `/docs`. Exemplos (sem acento: no terminal do Windows, acento na linha de comando chega ao `curl` fora de UTF-8; para testar com acentos, use o `/docs`):

```bash
curl -X POST http://127.0.0.1:8000/books -H "Content-Type: application/json" -d '{"title": "Dom Casmurro", "author": "Machado de Assis", "publication_date": "1899-01-01", "summary": "Bentinho narra o ciume que sente de Capitu."}'
```

```bash
curl "http://127.0.0.1:8000/books?author=machado"
```

A busca devolve `{"items": [...], "limit": 20, "offset": 0, "has_more": false}`, com cada item no formato do livro que o cadastro devolve. Dado inválido volta como 422 no formato do pydantic, com o campo em `loc`, venha o erro do schema ou de uma regra do livro. Acima do limite de requisições, a resposta é 429 com `Retry-After`.

Configuração por variável de ambiente, toda opcional. Para mudar algum valor, copie o [`.env.example`](.env.example) para `.env` e rode `uv run --env-file .env library`.

| Variável | Padrão | Para que serve |
| --- | --- | --- |
| `LIBRARY_DATABASE_PATH` | `library.db` | arquivo do SQLite |
| `LIBRARY_TIMEZONE` | `America/Sao_Paulo` | fuso da biblioteca, que define o "hoje" de `is_published` |
| `LIBRARY_RATE_LIMIT_REQUESTS` | `60` | requisições permitidas por cliente a cada janela |
| `LIBRARY_RATE_LIMIT_WINDOW_SECONDS` | `60` | tamanho da janela do rate limiting |

Testes, estilo e tipos:

```bash
uv run pytest
```

```bash
uv run ruff check .
```

```bash
uv run ruff format --check .
```

```bash
uv run mypy
```

## Estrutura

```
src/library/
├── domain/           entidade Book, PublicationDate, porta do repositório e erros
├── application/      casos de uso (cadastrar, buscar) e DTOs
├── infrastructure/   conexão, schema e repositório SQLite
└── api/              rotas, schemas HTTP, rate limiting e configuração
tests/                uma pasta por camada; infraestrutura e API contra SQLite real
docs/                 ADRs e qualidade.md (testes e bugs registrados)
```

As dependências apontam para dentro: `api` → `application` → `domain` ← `infrastructure` ([ADR 0001](docs/adr/0001-ddd-enxuto-em-camadas.md)).

## Decisões

O porquê de cada decisão, com as alternativas descartadas, está nas [ADRs desta questão](docs/adr/README.md). As que valem para o repositório inteiro estão no [README da raiz](../README.md).

1. [DDD enxuto, em camadas, com a aplicação como única porta da API](docs/adr/0001-ddd-enxuto-em-camadas.md)
2. [Entidade válida por construção, com identidade própria](docs/adr/0002-entidade-valida-com-identidade-propria.md)
3. [Instantes em UTC, data de publicação como dia, publicação derivada](docs/adr/0003-datas-e-estado-de-publicacao.md)
4. [Persistência com `sqlite3` da stdlib, num repositório único](docs/adr/0004-persistencia-sqlite3-com-repositorio-unico.md)
5. [Busca parcial, sem diferenciar maiúsculas nem acentos](docs/adr/0005-busca-sem-caixa-e-sem-acento.md)
6. [Contrato HTTP com paginação obrigatória e validação estrita na borda](docs/adr/0006-contrato-http-paginado-e-validacao-na-borda.md)
7. [Rate limiting próprio, por IP, em janela fixa e em memória](docs/adr/0007-rate-limiting-proprio-em-memoria.md)

## Testes

A suíte cobre domínio, repositório contra SQLite real, aplicação e API de ponta a ponta. Cada teste protege uma regra de negócio, e todo bug encontrado virou um teste antes da correção. Os bugs registrados e o que ficou de fora estão em [`docs/qualidade.md`](docs/qualidade.md).
