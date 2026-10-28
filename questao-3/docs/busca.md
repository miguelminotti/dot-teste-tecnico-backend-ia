# Busca: da consulta aos artigos

Como uma consulta em texto vira a lista dos artigos mais relevantes, sobre o índice descrito em [`indexacao.md`](indexacao.md). O código está em `src/semantic_search/search.py`.

```bash
uv run semantic-search "como avaliar agentes de programação" --k 5
```

## Como funciona

1. **A consulta vira um embedding,** com o mesmo modelo dos pedaços e o prefixo de consulta dele (`query: ` no e5).
2. **O FAISS devolve os pedaços mais parecidos,** pelo cosseno.
3. **Os pedaços são agrupados por artigo, e cada artigo vale pelo seu melhor pedaço.** O enunciado pede documentos, e o índice guarda pedaços. A nota do artigo é a do pedaço mais parecido com a consulta, que é também o trecho mostrado no resultado. A alternativa, somar ou tirar a média das notas dos pedaços, favorece artigos longos, com mais pedaços parecidos entre si, e não diz qual trecho responde à consulta.
4. **A busca garante `k` artigos.** A primeira tentativa busca 10 pedaços por artigo pedido. Quando os mais parecidos se concentram em menos de `k` artigos, o número de pedaços dobra até completar `k` ou chegar ao fim do índice.

O resultado é exato, e não uma aproximação da agregação. Um artigo que não aparece entre os pedaços buscados tem todos os pedaços abaixo do último deles e, portanto, nota menor que a de qualquer artigo achado.

Cada resultado traz o título, o link do arXiv, a nota e o trecho, com a seção de onde ele veio:

```text
1. [0.923] AccentCL: Robust Accent Classification with Incremental Expansion
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

search = SemanticSearch.load(
    "intfloat/multilingual-e5-base", index=Path("data/index"), corpus=Path("data/corpus.jsonl")
)
for result in search.search("class-incremental accent classification", k=3):
    print(result.score, result.title, result.url, result.excerpt.section)
```

A carga do modelo leva alguns segundos e acontece uma vez. Depois, cada consulta custa o embedding (12,9 ms na GPU) mais a busca no índice (2,5 ms de mediana).
