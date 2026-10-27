# ADR 0009: Camada de aplicação como única porta da API, devolvendo DTOs

- **Status:** Aceita
- **Data:** 2026-10-27

## Contexto

A API precisa cadastrar e buscar livros. Se as rotas montassem a entidade e chamassem o repositório direto, cada rota conheceria o banco, o domínio e o HTTP ao mesmo tempo. Se devolvessem a entidade `Book`, o contrato da API ficaria preso à forma interna do domínio (o value object `PublicationDate`, por exemplo) e quem consome poderia chamar comportamento da entidade.

## Decisão

- A camada `application` tem o `BookService`, com os casos de uso `register` e `search`. A API fala só com ele.
- O `BookService` recebe o repositório pela porta do domínio (`BookRepository`), não pela classe SQLite. Quem monta as peças é a dependência da API (`get_book_service`).
- Entra um `RegisterBookCommand` e sai um `BookDTO` (ou uma `BookPage` de `BookDTO`), dataclasses imutáveis com tipos simples. A entidade nunca sai da aplicação.
- `is_published` é calculado aqui, no "hoje" da biblioteca: `today_in(fuso)` converte o instante do relógio do domínio (UTC) para o dia no fuso configurado. O `BookService` recebe esse "hoje" como função, e um mesmo "hoje" vale para todos os livros de uma resposta.
- A paginação pede ao repositório uma linha a mais que o limite e responde `has_more` sem `COUNT`.

## Alternativas consideradas

- **Rotas chamando o repositório:** menos arquivos, mas a regra de montar o livro e calcular `is_published` ficaria espalhada pelas rotas, e trocar o banco mexeria nelas.
- **Devolver a entidade ou um modelo pydantic da aplicação:** o primeiro expõe o domínio; o segundo faria a aplicação depender de pydantic. Os schemas pydantic ficam na API e convertem do DTO.
- **Um caso de uso por classe (`RegisterBook`, `SearchBooks`):** com dois casos de uso que dividem as mesmas dependências, uma classe com dois métodos é suficiente.
- **`COUNT` para devolver o total:** no `LIKE '%trecho%'`, o `COUNT` percorre a tabela de novo a cada página.

## Consequências

- A API pode mudar de framework sem tocar nas regras; a aplicação pode ser usada por outra porta de entrada (CLI, importação em lote).
- Existem dois "espelhos" do livro: `BookDTO` na aplicação e `BookResponse` na API. É o custo de a aplicação não depender de pydantic.
- Sem `total`, o cliente não sabe quantas páginas existem, só se há próxima.
- `created_at` não serve para ordenar nem desempatar: no Windows, dois cadastros na mesma fração de milissegundo podem receber o mesmo instante. A ordem estável vem do `id` ([ADR 0008](0008-busca-sem-caixa-e-sem-acento.md)).
