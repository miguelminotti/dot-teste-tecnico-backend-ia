# ADR 0007: Persistência com `sqlite3` da stdlib, num repositório único

- **Status:** Aceita
- **Data:** 2026-10-27

## Contexto

O enunciado pede SQLite. O sistema tem uma tabela, uma escrita (cadastro) e uma leitura (busca). A política de datas ([ADR 0002](0002-instantes-em-utc-datas-sem-fuso.md)) exige que o banco grave instantes em UTC com o offset explícito, e o adaptador padrão de `datetime` do `sqlite3` está deprecado desde o Python 3.12 e grava sem fuso.

## Decisão

- **Porta no domínio, implementação na infraestrutura.** `BookRepository` é um `Protocol` em `domain/repository.py`; `SqliteBookRepository` em `infrastructure/` o implementa. A aplicação depende só da porta.
- **`sqlite3` da biblioteca padrão, sem ORM.** SQL explícito e conversão manual entre linha e entidade: datas viram texto ISO 8601 antes de gravar (`created_at` sempre com microssegundos e `+00:00`), e a entidade é reidratada pelo construtor, então as invariantes rodam de novo na leitura.
- **Um repositório para leitura e escrita.** `add` e `search` no mesmo lugar, sobre o mesmo banco.
- **Schema com `CREATE TABLE IF NOT EXISTS`**, tabela `STRICT` e `CHECK`s que repetem no banco a política de datas: `publication_date` precisa ser um dia válido e `created_at` precisa terminar em `+00:00`.
- **Conexão injetada.** O repositório recebe a conexão pronta; quem a abre e fecha (a API, por requisição) controla o ciclo de vida. Cada `add` é uma transação própria (`with connection`).
- **Erros do banco não vazam.** Chave primária duplicada vira `BookAlreadyExistsError` (domínio); qualquer outra violação de integridade é bug e estoura como está.

## Alternativas consideradas

- **SQLAlchemy 2.0:** abstrai o dialeto e abre caminho para Alembic e Postgres, mas é uma dependência e uma camada de mapeamento a mais para uma tabela. Trocar de banco hoje reescreve só o repositório, que é o que a porta isola.
- **SQLModel:** idiomático com FastAPI, mas tende a fundir tabela, schema da API e entidade num modelo só, o que contraria o domínio puro ([ADR 0004](0004-entidade-valida-por-construcao.md)).
- **CQRS (repositórios ou modelos separados para leitura e escrita):** com um endpoint de cada, o mesmo banco e o mesmo repositório atendem os dois. Separar entra se leitura e escrita passarem a ter necessidades diferentes (volume, formato, banco).
- **Repositório em memória ou fake:** desnecessário; o SQLite em memória (`:memory:`) é o banco real e serve aos testes.
- **Migrations (Alembic):** sem dados em produção e com uma tabela, não há o que migrar. Entra na primeira mudança de schema.

## Consequências

- Nenhuma dependência nova.
- Os testes da infraestrutura rodam contra SQLite real em memória, sem simular o banco.
- Uma operação que precise de várias escritas atômicas vai exigir controle de transação acima do repositório (unit of work), hoje deixado de fora.
- A busca é sempre paginada: a porta exige `limit`, e o repositório recusa `limit < 1` e `offset < 0`, porque no SQLite `LIMIT -1` significa "sem limite" ([ADR 0010](0010-contrato-http-e-validacao-na-borda.md)).
