# Questão 3 - Busca semântica de documentos

Sistema de busca semântica: gera embeddings de um conjunto de documentos, guarda numa vector store e, dado um texto de consulta, devolve os documentos mais relevantes por similaridade semântica.

## Enunciado × status

| Requisito do enunciado | Status |
| --- | --- |
| Conjunto de documentos de texto (artigos ou posts de blog) | 100 artigos do arXiv de outubro de 2026, sob licença aberta, em texto limpo e com as seções ([`docs/corpus.md`](docs/corpus.md)) |
| Embeddings dos documentos com um modelo de embeddings | 5.398 pedaços (um por parágrafo, mais título e resumo) com o `intfloat/multilingual-e5-base`, local, pelo sentence-transformers ([`docs/indexacao.md`](docs/indexacao.md)) |
| Embeddings armazenados numa vector store (FAISS ou Milvus) | Índice FAISS de busca exata (`IndexFlatIP`, cosseno), gravado ao lado dos pedaços ([`docs/indexacao.md`](docs/indexacao.md)) |
| Função de busca que devolve os documentos mais relevantes para uma consulta | `SemanticSearch.search` e a CLI `semantic-search`: os artigos mais relevantes, cada um pelo melhor pedaço, com título, link e trecho ([`docs/busca.md`](docs/busca.md)) |
| Processo de criação dos embeddings e do armazenamento documentado | pedaços, embeddings e vector store em [`docs/indexacao.md`](docs/indexacao.md) |
| Exemplos de consultas e resultados relevantes | pendente |

## Como rodar

Pré-requisito: [uv](https://docs.astral.sh/uv/). O uv baixa o Python 3.12 sozinho se ele não estiver instalado.

```bash
uv sync
```

O corpus vem no repositório; o índice não. Para gerá-lo e buscar:

```bash
uv run semantic-search-embed --model intfloat/multilingual-e5-base
uv run semantic-search-store --model intfloat/multilingual-e5-base
uv run semantic-search "como avaliar agentes de programação" --k 5
uv run semantic-search "Rogan–Gladen correction" --k 3 --method hybrid
```

O primeiro comando baixa o modelo (cerca de 1 GB) e leva uns 16 minutos na CPU; com uma GPU NVIDIA, menos de 1 minuto (veja [`docs/indexacao.md`](docs/indexacao.md)).

Os comandos de qualidade (ruff, mypy, pytest) e as convenções do código estão no [README da raiz](../README.md).

## Avaliação

A busca é desenvolvida guiada por avaliação: as consultas de teste, com os artigos e trechos relevantes, vieram antes da escolha do modelo de embeddings. São 99 consultas em inglês e português, de quatro tipos (pelo nome, por paráfrase, por detalhe e por tema), geradas por um LLM, rotuladas por um juiz sobre o corpus inteiro e revisadas uma a uma. O conjunto, como foi feito, as métricas e as limitações estão em [`docs/avaliacao.md`](docs/avaliacao.md).

```bash
uv run semantic-search-eval --model intfloat/multilingual-e5-base
```

Na linha de base, só com embeddings, os 10 primeiros resultados trazem em média 92,9% dos artigos relevantes, e o MRR é de 0,920. A busca vai pior com consultas em português, temas largos e o parágrafo exato de um detalhe. A busca híbrida (embeddings e BM25, fundidos pelo RRF) sobe o MRR em inglês de 0,945 para 0,985, mas derruba o português de 0,895 para 0,778, e por isso não é o padrão. Os números, a análise dos erros e os próximos experimentos estão em [`docs/experimentos.md`](docs/experimentos.md).
