# ADR 0006: Contrato HTTP com paginação obrigatória e validação estrita na borda

- **Status:** Aceita
- **Data:** 2026-10-27

## Contexto

O enunciado não pede autenticação, e ela ficou de fora. Isso pressupõe uso em ambiente controlado; exposta publicamente, a API precisaria de autenticação antes de qualquer outra proteção. Mesmo assim, ela recebe dados de fora: listas sem limite derrubam a resposta quando o acervo cresce, e o modo padrão do pydantic aceita entradas que viram dado errado em silêncio (o número `0` vira a data 01/01/1970).

## Decisão

- **Sem autenticação nem autorização.** A proteção mínima é o rate limiting ([ADR 0007](0007-rate-limiting-proprio-em-memoria.md)).
- **Paginação obrigatória por `limit` e `offset`**, com tetos para os dois. A resposta diz se há próxima página (`has_more`) em vez de trazer o total: a aplicação pede uma linha a mais que o limite e só olha se ela veio.
- **Validação estrita só onde o modo padrão erra em silêncio:** a data de publicação só é aceita como texto `AAAA-MM-DD`; campo desconhecido é erro, para o cliente não achar que conseguiu definir o id ou o estado de publicação; filtro de busca em branco é recusado, senão "contém vazio" casaria com o acervo inteiro.
- **Tetos de tamanho nos textos** como proteção da borda, não como regra de negócio ([ADR 0002](0002-entidade-valida-com-identidade-propria.md)).
- **O 422 tem um formato só**, o mesmo do pydantic, com o campo violado no `loc`, venha o erro do schema ou do domínio. Assim o cliente trata igual um título vazio e um título só com espaços.
- **O contrato documenta só o que a API devolve.** O id é gerado no domínio, então nenhuma requisição produz um livro duplicado: o 409 existe como defesa, mas fica fora do contrato.

## Alternativas consideradas

- **Paginação por cursor:** estável com inserções concorrentes e rápida em acervo grande, mas mais complexa de implementar e de usar. `limit/offset` basta para o tamanho de uma biblioteca.
- **Devolver o total com `COUNT`:** na busca por trecho, o `COUNT` percorreria a tabela de novo a cada página.
- **Modo `strict` global do pydantic:** o FastAPI valida o corpo em modo Python, e o modo estrito recusaria a data enviada como texto. A validação estrita ficou só onde importa.
- **`GET /books/{id}` com `Location` no 201:** o enunciado não pede, e o 201 já devolve o livro criado.

## Consequências

- Sem o total, o cliente não sabe quantas páginas existem, só se há próxima.
- As mensagens de validação do pydantic saem em inglês, e as do domínio em português.
- Um acervo grande o bastante para estourar o teto do `offset` pede paginação por cursor.
