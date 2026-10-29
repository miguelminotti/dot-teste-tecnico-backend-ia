# Busca: da consulta aos artigos

Como uma consulta em texto vira a lista dos artigos mais relevantes, sobre o índice descrito em [`indexacao.md`](indexacao.md). O código está em `src/semantic_search/search.py`.

```bash
uv run semantic-search "como avaliar agentes de programação" --k 5
```

## Como funciona

1. **A consulta vira um embedding,** com o mesmo modelo dos pedaços: o `BAAI/bge-m3` por padrão, ou outro com `--model` ([ADR 0001](adr/0001-modelo-de-embeddings-bge-m3.md)). O modelo que tem prefixo de consulta recebe o dele (`query: ` no e5).
2. **O FAISS devolve os pedaços mais parecidos,** pelo cosseno. Com `--method bm25`, a busca é por termos; com `--method hybrid`, as duas listas são fundidas pelo RRF. O padrão é só embeddings, que mediu melhor no conjunto inteiro ([`experimentos.md`](experimentos.md#bm25-e-busca-híbrida)). A nota mostrada muda com a busca: o cosseno nos embeddings, a nota do BM25 na busca por termos e a do RRF na híbrida (no máximo 2/61, cerca de 0,033, para um pedaço em 1º nas duas listas). O cosseno também muda de escala com o modelo, e só serve para ordenar dentro de uma busca: o mesmo pedaço, para a mesma consulta, tem 0,923 no e5 e 0,715 no bge-m3.
3. **Os pedaços são agrupados por artigo, e cada artigo vale pelo seu melhor pedaço.** O enunciado pede documentos, e o índice guarda pedaços. A nota do artigo é a do pedaço mais parecido com a consulta, que é também o trecho mostrado no resultado. A alternativa, somar ou tirar a média das notas dos pedaços, favorece artigos longos, com mais pedaços parecidos entre si, e não diz qual trecho responde à consulta.
4. **A busca completa `k` artigos.** A primeira tentativa busca 10 pedaços por artigo pedido. Quando os mais parecidos se concentram em menos de `k` artigos, o número de pedaços dobra até completar `k` ou chegar ao fim do índice. Só o BM25 pode devolver menos: ele não traz pedaços sem nenhum termo da consulta.

O resultado é exato, e não uma aproximação da agregação. Um artigo que não aparece entre os pedaços buscados tem todos os pedaços abaixo do último deles e, portanto, nota menor que a de qualquer artigo achado.

Cada resultado traz o título, o link do arXiv, a nota e o trecho, com a seção de onde ele veio:

```text
1. [0.715] AccentCL: Robust Accent Classification with Incremental Expansion
   https://arxiv.org/abs/2610.07426
   Discussion: We proposed AccentCL, a framework for English accent classification that supports
   class-incremental expansion. By combining data from new accents with replay memory stratified by
   dataset, AccentCL adds Spanish- and Chinese-accented English without retraining on the full old
   dataset. In our [...]
```

A saída sai sempre em UTF-8. Redirecionada para um arquivo, a saída do Python no Windows usa o cp1252, que não tem alguns caracteres dos artigos ("≥", "∎", letras gregas). São 56 dos 5.398 pedaços, e a busca caía com `UnicodeEncodeError` quando um deles aparecia no resultado.

## Para usar no código

```python
from pathlib import Path

from semantic_search.search import SemanticSearch

search = SemanticSearch.load("BAAI/bge-m3", index=Path("data/index"), corpus=Path("data/corpus.jsonl"))
for result in search.search("class-incremental accent classification", k=3):
    print(result.score, result.title, result.url, result.excerpt.section)
```

A carga do modelo leva alguns segundos e acontece uma vez. Depois, cada consulta custa o embedding (23 ms na GPU com o bge-m3) mais a busca no índice (de 1 a 3 ms).
