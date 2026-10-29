import pytest

from semantic_search.chunking import Chunk
from semantic_search.retrievers import BM25Retriever, HybridRetriever, Query
from semantic_search.vector_store import Hit


def _chunk(name: str, text: str = "") -> Chunk:
    return Chunk(id=name, paper_id="p", section="s", paragraph=0, text=text)


def _query(text: str) -> Query:
    return Query(text=text, vector=None)


def test_bm25_matches_words_by_their_stem() -> None:
    # "running dogs" casa com "the dog runs": o radical de cada palavra, e não a forma exata.
    retriever = BM25Retriever([_chunk("a", "The cat sat on the mat"), _chunk("b", "Every morning the dog runs")])

    hits = retriever.search(_query("running dogs"), n=2)

    assert [hit.chunk.id for hit in hits] == ["b"]


def test_bm25_returns_only_chunks_that_share_a_term_with_the_query() -> None:
    # O bm25s devolve também os pedaços de nota 0, numa ordem arbitrária, que na híbrida viraria ruído.
    # Uma consulta em português sobre o corpus em inglês costuma não ter termo nenhum em comum.
    chunks = [_chunk("a", "The cat sat on the mat"), _chunk("b", "Dogs in the park"), _chunk("c", "A cat and a dog")]
    retriever = BM25Retriever(chunks)

    assert {hit.chunk.id for hit in retriever.search(_query("dog"), n=10)} == {"b", "c"}
    assert retriever.search(_query("como gatos correm"), n=10) == []


def test_bm25_ignores_portuguese_stopwords() -> None:
    # "de" existe no corpus ("de Vries"): sem a lista do português, toda consulta em português casaria por ele.
    retriever = BM25Retriever([_chunk("a", "As shown by de Vries et al."), _chunk("b", "Accent classification")])

    assert retriever.search(_query("classificação de sotaque"), n=10) == []


class _FixedRetriever:
    """Retriever de teste: devolve sempre a mesma lista, cortada em n."""

    def __init__(self, *names: str) -> None:
        self._hits = [Hit(chunk=_chunk(name), score=1.0) for name in names]

    def __len__(self) -> int:
        return 10

    def search(self, query: Query, n: int) -> list[Hit]:
        return self._hits[:n]


def test_rrf_puts_a_chunk_ranked_second_by_both_above_one_ranked_first_by_only_one() -> None:
    # c vale 1/62 + 1/62; x e y, 1/61 cada. Com n=1, c só aparece se cada lista for além do 1º lugar.
    hybrid = HybridRetriever([_FixedRetriever("x", "c"), _FixedRetriever("y", "c")], k=60)

    hits = hybrid.search(_query("q"), n=1)

    assert [hit.chunk.id for hit in hits] == ["c"]
    assert hits[0].score == pytest.approx(2 / 62)


def test_rrf_keeps_chunks_found_by_only_one_retriever() -> None:
    hybrid = HybridRetriever([_FixedRetriever("x", "c"), _FixedRetriever("y", "c")], k=60)

    hits = hybrid.search(_query("q"), n=3)

    assert [hit.chunk.id for hit in hits][0] == "c"
    assert {hit.chunk.id for hit in hits} == {"c", "x", "y"}
