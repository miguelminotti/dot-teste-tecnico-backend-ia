# ADR 0010: Contrato HTTP com paginação obrigatória e validação estrita na borda

- **Status:** Aceita
- **Data:** 2026-10-27

## Contexto

O enunciado não pede autenticação, e ela ficou de fora. Isso pressupõe uso em ambiente controlado (uma rede interna, por exemplo); exposta publicamente, a API precisaria de autenticação antes de qualquer outra proteção. Mesmo nesse cenário, ela recebe dados de fora: listas sem limite derrubam a resposta quando o acervo cresce, e o modo padrão do pydantic aceita entradas que viram dado errado em silêncio (`0` vira a data 01/01/1970).

## Decisão

- **Sem autenticação nem autorização**, porque o enunciado não pede. A proteção mínima é o rate limiting ([ADR 0011](0011-rate-limiting-proprio-em-memoria.md)).
- **Dois endpoints:** `POST /books` (201, devolve o livro criado) e `GET /books` (busca paginada).
- **Paginação obrigatória:** `limit` (padrão 20, máximo 100) e `offset`, com resposta `{items, limit, offset, has_more}`. A porta do repositório exige `limit`, então nenhuma chamada devolve o acervo inteiro, e o repositório recusa `limit < 1`, porque no SQLite `LIMIT -1` significa "sem limite".
- **Validação estrita na borda:**
  - `publication_date` só como texto `AAAA-MM-DD`: número e data com hora são recusados;
  - campos desconhecidos são erro (`extra="forbid"`), para o cliente não achar que conseguiu definir `id`, `created_at` ou `is_published`;
  - tetos de tamanho: título 300, autor 200, resumo 5000 caracteres; filtros de busca 300 e 200;
  - filtro de busca só com espaços é recusado, senão "contém vazio" casaria com o acervo inteiro.
- **Erros de domínio viram HTTP num lugar só** (handlers em `app.py`): `BookAlreadyExistsError` → 409, qualquer outro `DomainError` → 422, com `{"detail": "..."}`.
- **Conexão por requisição**, aberta numa dependência e fechada ao fim, mesmo com erro. Ela é criada com `check_same_thread=False`, porque o FastAPI pode abrir a conexão numa thread do pool e usá-la em outra; é seguro porque a conexão nunca é compartilhada entre requisições.
- **Schema garantido na subida** (lifespan), com `CREATE TABLE IF NOT EXISTS`.
- **Configuração por variável de ambiente** (`LIBRARY_DATABASE_PATH`, `LIBRARY_TIMEZONE`, `LIBRARY_RATE_LIMIT_REQUESTS`, `LIBRARY_RATE_LIMIT_WINDOW_SECONDS`), com `create_app(settings)` para os testes passarem a sua.

## Alternativas consideradas

- **Paginação por cursor:** estável com inserções concorrentes e rápida em acervo grande, mas mais complexa de implementar e de usar. `limit/offset` basta para o tamanho de uma biblioteca.
- **Modo `strict` global do pydantic:** o FastAPI valida o corpo em modo Python, e o modo estrito recusaria a data enviada como texto. A validação estrita ficou só onde importa, na data.
- **`GET /books/{id}` com `Location` no 201:** não pedido pelo enunciado; o 201 já devolve o livro criado.

## Consequências

- As mensagens de validação do pydantic saem em inglês, e as do domínio em português.
- Rodar com mais de um worker exige um rate limiter compartilhado ([ADR 0011](0011-rate-limiting-proprio-em-memoria.md)).
