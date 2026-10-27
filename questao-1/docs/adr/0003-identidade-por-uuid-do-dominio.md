# ADR 0003: Identidade por UUID gerado no domínio

- **Status:** Aceita
- **Data:** 2026-10-27

## Contexto

Uma entidade precisa de identidade estável. Se o id vem do banco (autoincremento), o livro existe sem id até ser salvo, e o tipo vira `id: int | None`, espalhando checagens de `None`. Além disso, ids sequenciais na URL (`/books/42`) revelam quantos livros existem e permitem varrer o acervo.

## Decisão

- O `Book` nasce com `id: UUID` gerado por `uuid4()` no próprio domínio, antes de tocar o banco.
- Entidades se comparam pela identidade: `__eq__` e `__hash__` usam só o `id`. Dois livros com mesmos dados e ids diferentes são livros diferentes; o mesmo `id` com dados corrigidos continua sendo o mesmo livro.

## Alternativas consideradas

- **Autoincremento do SQLite:** mais simples e legível na URL, mas com id opcional na entidade e o volume do acervo exposto.
- **Igualdade por atributos (padrão da dataclass):** duas edições com mesmo título e autor se fundiriam num `set` ou numa deduplicação.

## Consequências

- O repositório grava o UUID; a chave primária no SQLite será texto (ou blob) em vez de inteiro.
- Testes podem montar livros com id fixo para simular o mesmo registro lido duas vezes.
- Abre espaço para campos como editora e edição no futuro: duas edições do mesmo título e autor já são livros distintos.
