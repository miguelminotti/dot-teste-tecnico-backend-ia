# ADR 0003: Código em inglês, documentação em português

- **Status:** Aceita
- **Data:** 2026-10-27

## Contexto

O enunciado está em português e fala em "livro", "título" e "data de publicação". Ao mesmo tempo, identificadores em inglês leem melhor ao lado das bibliotecas e da própria linguagem, que são todas em inglês. A primeira versão do domínio da questão 1 foi escrita em português (`Livro`, `titulo`) e renomeada antes do primeiro commit do domínio.

## Decisão

Identificadores ficam em inglês: classes, funções, variáveis, módulos, pacotes e o contrato JSON da API. Comentários, docstrings, mensagens de erro, READMEs e ADRs ficam em português. Ao citar código na documentação, usa-se o nome em inglês, sem glossário.

A regra principal é não misturar idiomas dentro do código: `Book` com `title`, nunca `Livro` com `author`.

## Alternativas consideradas

- **Tudo em português:** mantém a linguagem do enunciado no código, mas mistura com a API das bibliotecas (`Livro.model_validate`, `session.add(livro)`).
- **Glossário do enunciado para o código:** descartado por ser uma camada a mais de documentação; os nomes em inglês são traduções diretas.

## Consequências

- Os campos JSON da API seguem os nomes do domínio (`title`, `author`), sem camada de tradução no schema.
- Quem lê o README em português encontra os nomes do código em inglês entre crases.
