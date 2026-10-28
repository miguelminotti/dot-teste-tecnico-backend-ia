# ADR 0001: DDD enxuto, em camadas, com a aplicação como única porta da API

- **Status:** Aceita
- **Data:** 2026-10-27

## Contexto

O sistema é pequeno (uma entidade, cadastro e busca), mas o que ele tem de interessante para mostrar é o domínio: o livro e suas regras. Uma estrutura plana, com as rotas montando a entidade e acessando o banco, esconde as regras no meio do código de framework, e cada rota passa a conhecer HTTP, domínio e SQL ao mesmo tempo. Uma estrutura DDD completa (agregados, eventos, value object para cada campo) seria cerimônia sem regra para proteger.

## Decisão

- Quatro camadas: domínio (entidade, value objects e erros, em Python puro), aplicação (casos de uso), infraestrutura (SQLite) e API (FastAPI e pydantic).
- As dependências apontam para dentro: as rotas conhecem só a aplicação, e o domínio não conhece nenhuma outra camada. A exceção é o ponto de montagem da API, que liga a aplicação ao SQLite e traduz os erros do domínio em HTTP.
- A aplicação recebe o repositório pela porta definida no domínio, não pela implementação SQLite. Entra um comando e sai um DTO com tipos simples; a entidade nunca sai da aplicação.
- Value object só onde há regra e comportamento a proteger (ver [ADR 0003](0003-datas-e-estado-de-publicacao.md)); título e autor ficam como texto.

## Alternativas consideradas

- **Estrutura plana:** mais rápida de escrever, mas mistura regra de negócio com HTTP e SQL, e trocar o banco ou a interface mexe nas regras.
- **DDD completo:** agregados, eventos de domínio e value object por campo não têm função com uma entidade e duas operações.
- **Devolver a entidade para a API:** prende o contrato HTTP à forma interna do domínio, e quem consome passa a poder chamar comportamento da entidade.
- **Devolver um modelo pydantic da aplicação:** faria a aplicação depender de uma biblioteca de serialização.
- **Um caso de uso por classe:** com dois casos de uso que dividem as mesmas dependências, uma classe com dois métodos basta.

## Consequências

- O domínio é testado sem banco nem servidor.
- Trocar o SQLite por outro banco, ou expor o domínio por outra porta (CLI, importação em lote), não toca nas regras.
- Existem dois espelhos do livro: o DTO da aplicação e o schema da API. É o custo de a aplicação não depender de pydantic.
- Novas peças (agregados, eventos) têm lugar definido quando o domínio crescer, por exemplo com empréstimos e exemplares.
