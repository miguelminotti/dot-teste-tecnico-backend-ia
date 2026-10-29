# Questão 3 - Busca semântica de documentos

Sistema de busca semântica: gera embeddings de um conjunto de documentos, guarda numa vector store e, dado um texto de consulta, devolve os documentos mais relevantes por similaridade semântica.

## Enunciado × status

| Requisito do enunciado | Status |
| --- | --- |
| Conjunto de documentos de texto (artigos ou posts de blog) | 100 artigos do arXiv de outubro de 2026, sob licença aberta, em texto limpo e com as seções ([`docs/corpus.md`](docs/corpus.md)) |
| Embeddings dos documentos com um modelo de embeddings | 5.032 pedaços (um por parágrafo, mais título e resumo) com o `BAAI/bge-m3`, local, pelo sentence-transformers; o `intfloat/multilingual-e5-base` como opção leve ([`docs/indexacao.md`](docs/indexacao.md), [ADR 0001](docs/adr/0001-modelo-de-embeddings-bge-m3.md)) |
| Embeddings armazenados numa vector store (FAISS ou Milvus) | Índice FAISS de busca exata (`IndexFlatIP`, cosseno), gravado ao lado dos pedaços ([`docs/indexacao.md`](docs/indexacao.md)) |
| Função de busca que devolve os documentos mais relevantes para uma consulta | `SemanticSearch.search` e a CLI `semantic-search`: os artigos mais relevantes, cada um pelo melhor pedaço, com título, link e trecho ([`docs/busca.md`](docs/busca.md)) |
| Processo de criação dos embeddings e do armazenamento documentado | pedaços, embeddings e vector store em [`docs/indexacao.md`](docs/indexacao.md) |
| Exemplos de consultas e resultados relevantes | 7 buscas reais da CLI, em inglês e português (pelo nome, por paráfrase, por detalhe, por tema e uma livre), conferidas com os rótulos, incluindo os casos em que a busca erra ([`docs/exemplos.md`](docs/exemplos.md)) |

## Como rodar

Pré-requisito: [uv](https://docs.astral.sh/uv/). O uv baixa o Python 3.12 sozinho se ele não estiver instalado.

```bash
uv sync
```

O corpus vem no repositório; o índice não. Para gerá-lo e buscar:

```bash
uv run semantic-search-embed
uv run semantic-search-store
uv run semantic-search "como avaliar agentes de programação" --k 5
uv run semantic-search "Rogan–Gladen correction" --k 3 --method hybrid
```

O primeiro comando baixa o `BAAI/bge-m3` (4,3 GB) e gera os embeddings: menos de 3 minutos com uma GPU NVIDIA, cerca de 85 minutos na CPU (veja [`docs/indexacao.md`](docs/indexacao.md)). Para indexar mais rápido sem GPU, o `intfloat/multilingual-e5-base` baixa 1,1 GB e leva de 16 a 22 minutos na CPU, com pior resultado em consultas em português ([ADR 0001](docs/adr/0001-modelo-de-embeddings-bge-m3.md)). Os três comandos aceitam `--model intfloat/multilingual-e5-base`.

Os comandos de qualidade (ruff, mypy, pytest) e as convenções do código estão no [README da raiz](../README.md).

## Avaliação

A busca é desenvolvida guiada por avaliação: as consultas de teste, com os artigos e trechos relevantes, vieram antes da escolha do modelo de embeddings. São 99 consultas em inglês e português, de quatro tipos (pelo nome, por paráfrase, por detalhe e por tema), geradas por um LLM, rotuladas por um juiz sobre o corpus inteiro e revisadas uma a uma. O conjunto, como foi feito, as métricas e as limitações estão em [`docs/avaliacao.md`](docs/avaliacao.md).

```bash
uv run semantic-search-eval
```

O que os experimentos decidiram, com os números em [`docs/experimentos.md`](docs/experimentos.md):

- **Linha de base com o e5-base:** os 10 primeiros resultados trazem em média 92,7% dos artigos relevantes, e o MRR é de 0,920. A busca vai pior com consultas em português, temas largos e o parágrafo exato de um detalhe.
- **Busca híbrida (embeddings e BM25, fundidos pelo RRF):** sobe o MRR em inglês de 0,945 para 0,990, mas derruba o português de 0,895 para 0,794. Fica como opção (`--method hybrid`), e não como padrão.
- **bge-m3 no lugar do e5-base:** desfaz um erro sistemático em português, um artigo sobre LLM brasileiro que ficava em 1º no lugar do certo em 10 buscas e passa a ficar em 1. Nas médias, empata (MRR de 0,943 contra 0,920, dentro do ruído de 99 consultas). Virou o padrão ([ADR 0001](docs/adr/0001-modelo-de-embeddings-bge-m3.md)).
