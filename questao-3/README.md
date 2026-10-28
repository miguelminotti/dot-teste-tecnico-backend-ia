# Questão 3 - Busca semântica de documentos

Sistema de busca semântica: gera embeddings de um conjunto de documentos, guarda numa vector store e, dado um texto de consulta, devolve os documentos mais relevantes por similaridade semântica.

## Enunciado × status

| Requisito do enunciado | Status |
| --- | --- |
| Conjunto de documentos de texto (artigos ou posts de blog) | pendente |
| Embeddings dos documentos com um modelo de embeddings | pendente |
| Embeddings armazenados numa vector store (FAISS ou Milvus) | pendente |
| Função de busca que devolve os documentos mais relevantes para uma consulta | pendente |
| Processo de criação dos embeddings e do armazenamento documentado | pendente |
| Exemplos de consultas e resultados relevantes | pendente |

## Como rodar

Pré-requisito: [uv](https://docs.astral.sh/uv/). O uv baixa o Python 3.12 sozinho se ele não estiver instalado.

```bash
uv sync
```

Os comandos de qualidade (ruff, mypy) e as convenções do código estão no [README da raiz](../README.md).
