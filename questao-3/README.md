# Questão 3 - Busca semântica de documentos

Sistema de busca semântica: gera embeddings de um conjunto de documentos, guarda numa vector store e, dado um texto de consulta, devolve os documentos mais relevantes por similaridade semântica.

## Enunciado × status

| Requisito do enunciado | Status |
| --- | --- |
| Conjunto de documentos de texto (artigos ou posts de blog) | 100 artigos do arXiv de outubro de 2026, sob licença aberta, em texto limpo e com as seções ([`docs/corpus.md`](docs/corpus.md)) |
| Embeddings dos documentos com um modelo de embeddings | 5.032 pedaços (um por parágrafo, mais título e resumo) com o `BAAI/bge-m3`, local, pelo sentence-transformers; o `intfloat/multilingual-e5-base` como opção leve ([`docs/indexacao.md`](docs/indexacao.md), [ADR 0001](docs/adr/0001-modelo-de-embeddings-bge-m3.md)) |
| Embeddings armazenados numa vector store (FAISS ou Milvus) | Índice FAISS de busca exata (`IndexFlatIP`, cosseno), gravado ao lado dos pedaços e versionado ([`docs/indexacao.md`](docs/indexacao.md)) |
| Função de busca que devolve os documentos mais relevantes para uma consulta | `SemanticSearch.search` e a CLI `semantic-search`: os artigos mais relevantes, cada um pelo melhor pedaço, com título, link e trecho ([`docs/busca.md`](docs/busca.md)) |
| Processo de criação dos embeddings e do armazenamento documentado | pedaços, embeddings e vector store em [`docs/indexacao.md`](docs/indexacao.md) |
| Exemplos de consultas e resultados relevantes | 5 buscas reais da CLI, em inglês e português (pelo nome, por paráfrase, por tema, com a busca híbrida e uma livre), conferidas com os rótulos, incluindo os casos em que a busca erra ([`docs/exemplos.md`](docs/exemplos.md)) |

## Como rodar

Pré-requisito: [uv](https://docs.astral.sh/uv/), que baixa o Python 3.12 se ele não estiver instalado. O corpus e o índice do modelo padrão, o `BAAI/bge-m3`, vêm no repositório: a busca roda logo depois do `uv sync`, sem indexar.

```bash
uv sync
```

```bash
uv run semantic-search "como avaliar agentes de programação" --k 5
uv run semantic-search "Rogan–Gladen correction" --k 3 --method hybrid
```

A primeira busca baixa o bge-m3 (4,3 GB), que transforma a consulta em vetor. A busca híbrida (`--method hybrid`) ajuda em termos raros em inglês. Para reindexar depois de mudar o corpus ou a divisão em pedaços, `uv run semantic-search-embed` e `uv run semantic-search-store`: menos de 3 minutos numa GPU NVIDIA, cerca de 85 minutos na CPU ([`docs/indexacao.md`](docs/indexacao.md#2-embeddings)).

Com menos download, o `intfloat/multilingual-e5-base` baixa 1,1 GB, mas o índice dele não vem no repositório: indexar leva cerca de 22 minutos na CPU, e o resultado é pior em consultas em português ([ADR 0001](docs/adr/0001-modelo-de-embeddings-bge-m3.md)). Os três comandos aceitam `--model intfloat/multilingual-e5-base`.

Os comandos de qualidade (ruff, mypy, pytest) estão no [README da raiz](../README.md).

## Avaliação

São 99 consultas em inglês e em português, de quatro tipos (pelo nome, por paráfrase, por detalhe e por tema), rotuladas sobre o corpus inteiro e revisadas uma a uma ([`docs/avaliacao.md`](docs/avaliacao.md)); `uv run semantic-search-eval` roda a avaliação. Com o bge-m3, o modelo padrão, os 10 primeiros resultados trazem em média 93,7% dos artigos relevantes, com MRR de 0,943. Nas médias, ele empata com o e5-base (92,7% e 0,920, diferença dentro do ruído do conjunto), mas desfaz um erro sistemático em português: um artigo sobre LLM brasileiro que o e5 punha em 1º, no lugar do certo, em 10 buscas, e o bge-m3 em 1; por isso virou o padrão. A busca híbrida sobe o MRR em inglês de 0,948 para 0,985, mas derruba o português de 0,939 para 0,840, e fica como opção. A busca não tem limiar de relevância: devolve sempre os `k` artigos mais parecidos, mesmo para uma consulta sem relação com o corpus ([`docs/busca.md`](docs/busca.md)). Os números estão em [`docs/experimentos.md`](docs/experimentos.md).
