# Corpus da questão 3

O conjunto de documentos da busca semântica: 100 artigos de processamento de linguagem natural publicados no arXiv em outubro de 2026, em texto limpo e com as seções, em [`data/corpus.jsonl`](../data/corpus.jsonl). O código está em `src/semantic_search/corpus.py`.

## Por que artigos recentes do arXiv

- **Recentes, e cheios de nomes que não existiam.** Os artigos são do mês em que o corpus foi montado, depois do corte de treinamento de qualquer modelo de embeddings disponível. Trazem métodos e modelos novos (JudgeMoE, MemDuet, HarnessSQL, InsClaimBench), e é aí que a busca por embeddings tropeça: segundo a Chip Huyen (*AI Engineering*, 2025, cap. 6), converter o texto em embeddings pode apagar palavras-chave como nomes de produto, e a busca por termos (BM25) ou a combinação das duas (busca híbrida) recuperam o que o embedding perde. Um corpus assim mede essa diferença.
- **Longos.** O texto completo, e não só o resumo, porque como dividir o documento em pedaços (*chunking*) é uma das escolhas que mais mudam a qualidade da busca, e o livro diz que não há tamanho de pedaço universal: é preciso experimentar. Com resumos de 200 palavras não haveria o que dividir.
- **Com licença que permite redistribuir.** Só entram artigos sob CC BY 4.0 ou CC0, e o corpus fica no repositório, com a atribuição de cada artigo. Blogs de laboratórios e o blog da Hugging Face, alternativas naturais de "posts de blog", não têm licença aberta.
- **Artigos são o que o enunciado pede** ("um conjunto de artigos ou posts de um blog").

## Como o corpus é montado

```bash
uv run semantic-search-corpus
```

1. **Metadados.** Colhe pelo OAI-PMH do arXiv os registros de computação alterados de 1 a 27 de outubro de 2026: título, resumo, autores, categorias e licença de cada artigo. O fim do intervalo é um dia já fechado, para que rodar de novo dê os mesmos candidatos.
2. **Candidatos.** Ficam os artigos submetidos em outubro de 2026 com processamento de linguagem natural (`cs.CL`) como categoria principal e licença CC BY 4.0 ou CC0: 1.012 candidatos. O mês vem do id do arXiv, atribuído na primeira submissão. A data `created` do OAI não serve: um artigo de 2023 aparece nela com data de outubro de 2026.
3. **Sorteio.** Os candidatos são embaralhados com semente fixa (42) e o HTML de cada um é baixado até juntar 100 artigos, com 3 s entre requisições, como o arXiv pede. Cinco artigos não tinham HTML (a conversão do LaTeX falha em parte deles) e um ficou de fora por ter menos de 1.500 palavras no corpo, sinal de conversão incompleta. O HTML baixado fica em `data/html/`, fora do git, para que mudar a extração não peça baixar tudo de novo.
4. **Extração.** O HTML que o arXiv gera do LaTeX (LaTeXML) vira uma lista de seções, cada uma com o título, o nível (seção, subseção...) e os parágrafos.

| Parte do artigo | Tratamento | Por quê |
| --- | --- | --- |
| Título e resumo | dos metadados do OAI | o título do HTML traz notas grudadas ("Thanks: ...") |
| Corpo | seções e subseções na ordem, com o nível; cada parágrafo só na sua seção | a estrutura guia a divisão em pedaços; no HTML, o parágrafo da subseção também está dentro da seção pai e entraria duplicado |
| Referências | fora | trariam títulos de outros artigos para dentro deste |
| Apêndices | fora | são sobretudo detalhes de experimento e hiperparâmetros |
| Figuras e tabelas | fora | tabelas viram números soltos sem o cabeçalho; figuras às vezes trazem caixas de prompt sem contexto |
| Notas de rodapé | fora | agradecimentos, links e detalhes laterais |
| Fórmulas | trocadas pelo LaTeX original (`\mathcal{L}`) | o MathML traz a fórmula duas vezes, e o LaTeX é como os autores a escreveram |
| Numeração (de seção, equação, item) | fora | não diz nada sobre o conteúdo |
| Citações numéricas (`[3, 4]`) | fora | sem a lista de referências, o número não diz nada |
| Citações por autor e ano ("(Smith, 2025)") | ficam | fazem parte da frase |

O que sobra de colchete com número no texto são intervalos matemáticos (`[0,1]`), conteúdo de verdade, e citações que vêm com o nome do autor ("Chen et al. [4]").

## Formato

Um artigo por linha (JSONL):

```json
{
  "id": "2610.07109",
  "url": "https://arxiv.org/abs/2610.07109",
  "title": "JudgeMoE: Distributional Aggregation for LLM-as-a-Judge",
  "authors": ["..."],
  "categories": ["cs.CL", "cs.AI"],
  "license": "http://creativecommons.org/licenses/by/4.0/",
  "abstract": "...",
  "sections": [{"heading": "Introduction", "level": 1, "paragraphs": ["...", "..."]}]
}
```

## Números

| | |
| --- | --- |
| Artigos | 100 (97 sob CC BY 4.0, 3 sob CC0) |
| Palavras no corpo | 437.724; por artigo, de 1.910 a 16.118, mediana 3.990 |
| Seções | 2.637 |
| Parágrafos | 5.038; mediana de 76 palavras, 95% com até 188 |

## Licença e atribuição

Os textos são dos autores de cada artigo, sob a licença indicada no campo `license` da linha (CC BY 4.0 ou CC0). Cada linha traz a atribuição que a CC BY pede: título, autores, link para o artigo no arXiv e a licença. O texto foi modificado na extração descrita acima (sem referências, apêndices, figuras, tabelas, notas e citações numéricas, e com as fórmulas em LaTeX); o conteúdo que fica não foi editado.
