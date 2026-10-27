# ADR 0001: DDD enxuto, em camadas com dependências para dentro

- **Status:** Aceita
- **Data:** 2026-10-27

## Contexto

O sistema é pequeno (uma entidade, cadastro e busca), mas o que ele tem de interessante para mostrar é o domínio: o livro e suas regras. Uma estrutura plana (rotas acessando o banco direto) esconde as regras no meio do código de framework. Uma estrutura DDD completa (agregados, eventos, value object para cada campo, uma pasta por entidade) seria cerimônia sem regra para proteger.

## Decisão

Domain-Driven Design na medida do problema, com quatro camadas, cada uma numa pasta de `src/library/`, criada só quando for usada:

- `domain`: entidades, value objects e erros de domínio, em Python puro, sem framework nem banco.
- `application`: casos de uso (cadastrar, buscar).
- `infrastructure`: repositório SQLite.
- `api`: rotas FastAPI e schemas pydantic.

As dependências apontam para dentro: as rotas da API conhecem só a aplicação, e o domínio não conhece nenhuma outra camada. A exceção é o ponto de montagem da API (`app.py` e `dependencies.py`), que importa a infraestrutura para ligar o `BookService` ao SQLite e os erros do domínio para traduzi-los em HTTP.

Value object só onde há regra e comportamento a proteger (ver [ADR 0005](0005-publication-date-como-fonte-unica.md)); campos simples como `title` e `author` ficam como `str`.

## Alternativas consideradas

- **Estrutura plana:** mais rápida de escrever, mas mistura regra de negócio com HTTP e SQL, e trocar o banco ou a interface mexe nas regras.
- **DDD completo:** agregados, eventos de domínio e value object por campo não têm função com uma entidade e duas operações.

## Consequências

- O domínio é testado sem banco nem servidor (ver [ADR 0006](0006-testes-protegem-regras-de-negocio.md)).
- Trocar o SQLite por outro banco, ou expor o domínio por outra interface, não toca nas regras.
- Novas peças (agregados, eventos) têm lugar definido quando o domínio crescer, por exemplo com empréstimos e exemplares.
