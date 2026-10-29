from pathlib import Path

import faiss
import numpy as np
import pytest

from semantic_search.chunking import Chunk
from semantic_search.embeddings import EmbeddingIndex, Vectors, save_index
from semantic_search.vector_store import VectorStore


def _chunk(number: int) -> Chunk:
    return Chunk(id=f"p#{number}", paper_id="p", section="s", paragraph=number, text=f"texto {number}")


def _unit(*rows: list[float]) -> Vectors:
    vectors = np.array(rows, dtype=np.float32)
    return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


def _embedding_index(vectors: Vectors) -> EmbeddingIndex:
    return EmbeddingIndex(model="m", max_words=200, chunks=[_chunk(i) for i in range(len(vectors))], vectors=vectors)


def test_search_returns_chunks_from_most_to_least_similar_scored_by_cosine() -> None:
    vectors = _unit([0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.6, 0.8, 0.0])
    query = _unit([1.0, 0.2, 0.0])

    hits = VectorStore.build(_embedding_index(vectors)).search(query, k=3)[0]

    assert [hit.chunk.id for hit in hits] == ["p#1", "p#2", "p#0"]
    assert [hit.score for hit in hits] == pytest.approx((vectors @ query[0])[[1, 2, 0]], abs=1e-6)


def test_k_larger_than_the_store_returns_only_existing_chunks() -> None:
    # O FAISS completa as vagas com o id -1, e chunks[-1] devolveria o último pedaço em silêncio, repetido.
    store = VectorStore.build(_embedding_index(_unit([1.0, 0.0], [0.0, 1.0])))

    hits = store.search(_unit([1.0, 0.0]), k=5)[0]

    assert [hit.chunk.id for hit in hits] == ["p#0", "p#1"]


def test_vectors_without_unit_norm_are_rejected() -> None:
    # Sem norma 1, o produto interno deixa de ser o cosseno, e um vetor longo venceria por ser longo.
    vectors = np.array([[2.0, 0.0], [0.0, 1.0]], dtype=np.float32)

    with pytest.raises(ValueError, match="norma 1"):
        VectorStore.build(_embedding_index(vectors))


def test_saved_store_comes_back_with_the_same_hits_even_in_a_folder_with_accents(tmp_path: Path) -> None:
    # No Windows, o write_index e o read_index do FAISS não abrem caminho com acento, como o de um usuário
    # "C:\Users\João".
    folder = tmp_path / "pasta_ação"
    folder.mkdir()
    embedding_index = _embedding_index(_unit([0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.6, 0.8, 0.0]))
    store = VectorStore.build(embedding_index)
    query = _unit([1.0, 0.2, 0.0], [0.0, 0.1, 1.0])

    save_index(embedding_index, folder)
    store.save(folder)
    loaded = VectorStore.load(folder)

    assert loaded.search(query, k=3) == store.search(query, k=3)


def test_faiss_index_with_a_different_number_of_vectors_than_chunks_is_rejected() -> None:
    # Pega um faiss.index velho ao lado de pedaços regerados com outro corte: o vetor i não seria o pedaço i.
    faiss_index = faiss.IndexFlatIP(2)
    faiss_index.add(_unit([1.0, 0.0], [0.0, 1.0], [1.0, 1.0]))

    with pytest.raises(ValueError, match="3 vetores e 2 pedaços"):
        VectorStore(faiss_index, [_chunk(0), _chunk(1)])
