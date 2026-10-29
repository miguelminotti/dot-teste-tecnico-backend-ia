import io
import sys

import numpy as np
import pytest

from semantic_search.chunking import Chunk
from semantic_search.corpus import Document
from semantic_search.embeddings import EmbeddingIndex, Vectors
from semantic_search.retrievers import DenseRetriever, Query
from semantic_search.search import PaperResult, print_results, rank_papers
from semantic_search.vector_store import VectorStore


def _unit(*rows: list[float]) -> Vectors:
    vectors = np.array(rows, dtype=np.float32)
    return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


def _store(paper_ids: list[str], vectors: Vectors) -> DenseRetriever:
    chunks = [
        Chunk(id=f"{paper}#{i}", paper_id=paper, section="s", paragraph=i, text=f"texto {i}")
        for i, paper in enumerate(paper_ids)
    ]
    return DenseRetriever(VectorStore.build(EmbeddingIndex(model="m", max_words=200, chunks=chunks, vectors=vectors)))


def _documents(*paper_ids: str) -> dict[str, Document]:
    return {
        paper: Document(
            id=paper, title=f"Título {paper}", abstract="", sections=(), url=f"https://arxiv.org/abs/{paper}"
        )
        for paper in paper_ids
    }


def test_each_paper_appears_once_scored_and_excerpted_by_its_best_chunk() -> None:
    # A tem o pedaço mais parecido e também o menos parecido: aparece uma vez, em 1º, pelo melhor.
    store = _store(["A", "B", "A"], _unit([0.0, 1.0], [0.8, 0.6], [1.0, 0.1]))
    query = _unit([1.0, 0.0])

    results = rank_papers(store, Query(text="", vector=query), k=5, documents=_documents("A", "B"))

    assert [result.paper_id for result in results] == ["A", "B"]
    assert results[0].excerpt.id == "A#2"
    assert results[0].score == pytest.approx(float(_unit([1.0, 0.1])[0, 0]), abs=1e-6)
    assert (results[0].title, results[0].url) == ("Título A", "https://arxiv.org/abs/A")


def test_returns_k_papers_even_when_the_best_chunks_all_come_from_one_paper() -> None:
    # Os 200 pedaços mais parecidos são todos de A; B só aparece depois deles, e mesmo assim entra no top-2.
    angles = np.linspace(0.0, 0.5, 200)
    vectors = np.vstack([np.column_stack([np.cos(angles), np.sin(angles)]), [[0.0, 1.0]]]).astype(np.float32)
    store = _store(["A"] * 200 + ["B"], vectors)

    results = rank_papers(store, Query(text="", vector=_unit([1.0, 0.0])), k=2, documents=_documents("A", "B"))

    assert [result.paper_id for result in results] == ["A", "B"]


def test_k_larger_than_the_number_of_papers_returns_every_paper() -> None:
    store = _store(["A", "B"], _unit([1.0, 0.0], [0.0, 1.0]))

    results = rank_papers(store, Query(text="", vector=_unit([1.0, 0.0])), k=5, documents=_documents("A", "B"))

    assert [result.paper_id for result in results] == ["A", "B"]


def test_returns_at_most_k_papers_when_the_chunks_found_span_more() -> None:
    # No corpus, os pedaços da primeira tentativa costumam vir de mais artigos que os `k` pedidos.
    store = _store(["A", "B", "C"], _unit([1.0, 0.0], [0.8, 0.6], [0.0, 1.0]))

    results = rank_papers(store, Query(text="", vector=_unit([1.0, 0.0])), k=2, documents=_documents("A", "B", "C"))

    assert [result.paper_id for result in results] == ["A", "B"]


def test_results_are_printed_in_utf8_even_when_the_output_encoding_is_not(monkeypatch: pytest.MonkeyPatch) -> None:
    # Redirecionada para arquivo, a saída do Python no Windows usa o cp1252, e 56 pedaços do corpus têm
    # caracteres fora dele ("≥", letras gregas): a CLI caía com UnicodeEncodeError no meio dos resultados.
    buffer = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(buffer, encoding="cp1252"))
    excerpt = Chunk(id="A#0", paper_id="A", section="Setup", paragraph=0, text="Mantemos SNR ≥ 15 dB.")
    result = PaperResult(paper_id="A", title="Título A", url="https://arxiv.org/abs/A", score=0.9, excerpt=excerpt)

    print_results([result])
    sys.stdout.flush()

    assert "SNR ≥ 15 dB" in buffer.getvalue().decode("utf-8")
