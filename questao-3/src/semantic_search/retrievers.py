"""Os buscadores de pedaços: por embeddings, por termos (BM25) e a fusão dos dois (busca híbrida).

Todos recebem a mesma consulta, com o texto e o embedding, e devolvem os pedaços do mais para o menos
relevante. A busca por artigos (search.py) funciona sobre qualquer um deles.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import bm25s
import Stemmer
from bm25s.stopwords import STOPWORDS_EN, STOPWORDS_PORTUGUESE

from semantic_search.chunking import Chunk
from semantic_search.embeddings import Vectors
from semantic_search.vector_store import Hit, VectorStore

# Constante do RRF, a do artigo original (Cormack et al., 2009) e a que o livro cita: amortece a diferença
# entre as primeiras posições, para que um 1º lugar numa lista só não decida sozinho.
RRF_K = 60

_STOPWORDS = sorted(set(STOPWORDS_EN) | set(STOPWORDS_PORTUGUESE))


@dataclass(frozen=True, slots=True, kw_only=True)
class Query:
    """A consulta: o texto, para a busca por termos, e o embedding (uma linha), para a busca densa."""

    text: str
    vector: Vectors | None


class Retriever(Protocol):
    def __len__(self) -> int: ...

    def search(self, query: Query, n: int) -> list[Hit]:
        """Até `n` pedaços, do mais para o menos relevante."""
        ...


class DenseRetriever:
    """Busca por embeddings: os pedaços mais parecidos pelo cosseno, no índice FAISS."""

    def __init__(self, store: VectorStore) -> None:
        self._store = store

    def __len__(self) -> int:
        return len(self._store)

    def search(self, query: Query, n: int) -> list[Hit]:
        if query.vector is None:
            raise ValueError("a busca densa precisa do embedding da consulta")
        return self._store.search(query.vector, min(n, len(self._store)))[0]


class BM25Retriever:
    """Busca por termos com o BM25: casa as palavras da consulta com as dos pedaços, pesando as raras.

    As palavras passam para minúsculas, perdem as stopwords e são reduzidas ao radical (stemmer Snowball do
    inglês), para que "running dogs" case com "the dog runs". As stopwords são as do inglês e as do
    português, a língua da outra metade das consultas: "de", "em" e "que" aparecem no corpus ("de Vries"), e
    sem a lista toda consulta em português casaria por elas.
    """

    def __init__(self, chunks: Sequence[Chunk]) -> None:
        self._chunks = list(chunks)
        self._stemmer = Stemmer.Stemmer("english")
        self._bm25 = bm25s.BM25()
        self._bm25.index(self._tokenize([chunk.text for chunk in self._chunks]), show_progress=False)

    def __len__(self) -> int:
        return len(self._chunks)

    def search(self, query: Query, n: int) -> list[Hit]:
        ids, scores = self._bm25.retrieve(
            self._tokenize([query.text]), k=min(n, len(self._chunks)), show_progress=False
        )
        # O bm25s devolve também os pedaços sem termo nenhum da consulta, com nota 0 e em ordem arbitrária.
        return [
            Hit(chunk=self._chunks[int(i)], score=float(score))
            for i, score in zip(ids[0], scores[0], strict=True)
            if score > 0
        ]

    def _tokenize(self, texts: list[str]) -> list[list[str]]:
        tokens: list[list[str]] = bm25s.tokenize(
            texts, stopwords=_STOPWORDS, stemmer=self._stemmer, return_ids=False, show_progress=False
        )
        return tokens


class HybridRetriever:
    """Busca híbrida: funde as listas dos buscadores pelo RRF (*reciprocal rank fusion*).

    Cada pedaço soma 1 / (RRF_K + posição) em cada lista em que aparece. O RRF usa só as posições, e não as
    notas, que não se comparam entre buscadores (cosseno de um lado, BM25 do outro). A fusão é feita sobre
    as listas completas: cortadas em `n`, um pedaço em (n+1)º nas duas ficaria de fora, valendo mais que um
    que só uma delas pôs em 1º. Com 5 mil pedaços, a lista completa custa poucos milissegundos.
    """

    def __init__(self, retrievers: Sequence[Retriever], *, k: int = RRF_K) -> None:
        self._retrievers = list(retrievers)
        self._k = k

    def __len__(self) -> int:
        return max(len(retriever) for retriever in self._retrievers)

    def search(self, query: Query, n: int) -> list[Hit]:
        scores: dict[str, float] = {}
        chunks: dict[str, Chunk] = {}
        for retriever in self._retrievers:
            for position, hit in enumerate(retriever.search(query, len(retriever)), start=1):
                scores[hit.chunk.id] = scores.get(hit.chunk.id, 0.0) + 1 / (self._k + position)
                chunks[hit.chunk.id] = hit.chunk
        ranked = sorted(scores, key=lambda chunk_id: scores[chunk_id], reverse=True)
        return [Hit(chunk=chunks[chunk_id], score=scores[chunk_id]) for chunk_id in ranked[:n]]
