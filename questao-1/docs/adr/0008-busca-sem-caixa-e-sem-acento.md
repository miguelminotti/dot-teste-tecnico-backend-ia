# ADR 0008: Busca parcial, sem diferenciar maiúsculas nem acentos

- **Status:** Aceita
- **Data:** 2026-10-27

## Contexto

O enunciado pede consulta por título ou autor. Quem busca digita do jeito que lembra: "machado", "jose de alencar", "erico". O `LIKE` do SQLite só ignora maiúsculas em ASCII ("érico" não acha "Érico") e nunca ignora acentos ("jose" não acha "José"). Livro que não aparece na busca é livro que não é encontrado nem emprestado.

## Decisão

- A busca é por trecho ("contém"), em título e/ou autor. Com os dois filtros, o livro precisa casar com ambos.
- O repositório grava, ao lado de `title` e `author`, as colunas `title_search` e `author_search` com o texto normalizado, e busca nelas. O texto buscado passa pela mesma normalização.
- Normalizar é: `casefold` (maiúsculas, "ß" vira "ss"), NFKD (separa letra e acento, desfaz ligaduras) e descarte dos acentos soltos.
- `%` e `_` digitados pelo usuário são escapados e buscados como texto, não como curinga.
- O resultado vem em ordem alfabética de título e autor, com o `id` desempatando, para a ordem ser estável.

## Alternativas consideradas

- **`LIKE` nativo:** sem colunas extras, mas falha com acentos e com maiúsculas fora do ASCII, que são a maior parte dos nomes em português.
- **Busca exata:** pouco útil; ninguém digita o título completo e com a grafia exata.
- **Função de normalização registrada no SQLite (`create_function`) e aplicada na consulta:** evita as colunas extras, mas roda a função em todas as linhas a cada busca e precisa ser registrada em toda conexão.
- **FTS5 (busca textual do SQLite):** busca por palavra, com ranking. Mais poderosa, mas é outra estrutura de tabela para manter sincronizada, e o enunciado não pede ranking.

## Consequências

- A normalização é detalhe da infraestrutura: num banco com suporte nativo (Postgres com `unaccent` e `ILIKE`, por exemplo), as colunas extras podem sumir sem mudar a porta.
- `LIKE '%trecho%'` não usa índice, então a busca percorre a tabela. Para o tamanho do acervo de uma prova, é irrelevante; para um acervo grande, o caminho é FTS5 ou o banco de busca do Postgres.
- Se a regra de normalização mudar, as colunas `_search` existentes precisam ser recalculadas.
