# ADR 0005: Busca parcial, sem diferenciar maiúsculas nem acentos

- **Status:** Aceita
- **Data:** 2026-10-27

## Contexto

O enunciado pede consulta por título ou autor. Quem busca digita do jeito que lembra: "machado", "jose de alencar", "erico". O `LIKE` do SQLite só ignora maiúsculas em ASCII ("érico" não acha "Érico") e nunca ignora acentos ("jose" não acha "José"). Livro que não aparece na busca é livro que não é encontrado.

## Decisão

- A busca é por trecho ("contém"), em título e/ou autor. Com os dois filtros, o livro precisa casar com ambos.
- O repositório grava, ao lado do título e do autor, uma versão normalizada de cada um, e busca nela. O texto buscado passa pela mesma normalização.
- Normalizar é: `casefold` (maiúsculas, e "ß" vira "ss"), decomposição NFKD (separa letra e acento, desfaz ligaduras) e descarte dos acentos soltos.
- `%` e `_` digitados pelo usuário são buscados como texto, não como curinga.
- O resultado vem em ordem alfabética de título e autor, com o id desempatando, para que a paginação não repita nem pule livros.

## Alternativas consideradas

- **`LIKE` nativo:** sem colunas extras, mas falha com acentos e com maiúsculas fora do ASCII, que são a maior parte dos nomes em português.
- **Busca exata:** pouco útil; ninguém digita o título completo e com a grafia exata.
- **Função de normalização registrada no SQLite e aplicada na consulta:** evita as colunas extras, mas roda a função em todas as linhas a cada busca e precisa ser registrada em toda conexão.
- **FTS5 (busca textual do SQLite):** busca por palavra, com ranking. Mais poderosa, mas é outra estrutura para manter sincronizada, e o enunciado não pede ranking.

## Consequências

- A normalização é detalhe da infraestrutura: num banco com suporte nativo (Postgres com `unaccent` e `ILIKE`, por exemplo), as colunas extras podem sumir sem mudar a porta.
- Busca por "contém" não usa índice e percorre a tabela. Para o tamanho do acervo de uma prova, é irrelevante; para um acervo grande, o caminho é FTS5 ou a busca textual do Postgres.
- Se a regra de normalização mudar, as colunas normalizadas existentes precisam ser recalculadas.
