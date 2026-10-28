from pathlib import Path

import numpy as np
import pytest

from semantic_search.chunking import Chunk
from semantic_search.embeddings import EmbeddingIndex, load_index, prompts_for, save_index


def test_e5_models_get_the_query_and_passage_prefixes() -> None:
    # O e5 foi treinado com "query: " e "passage: " e a configuração dele no sentence-transformers vem
    # vazia: sem a tabela, consulta e documento saíam com o mesmo embedding, e a busca perdia qualidade
    # sem nenhum erro aparente.
    for model in ["intfloat/multilingual-e5-small", "intfloat/multilingual-e5-base", "intfloat/multilingual-e5-large"]:
        assert prompts_for(model) == {"query": "query: ", "document": "passage: "}


def test_model_without_entry_keeps_its_own_configuration() -> None:
    # Modelos como o Qwen3-Embedding trazem os próprios prompts; sobrescrevê-los com vazio os apagaria.
    assert prompts_for("Qwen/Qwen3-Embedding-0.6B") is None


def _chunk(number: int) -> Chunk:
    return Chunk(id=f"p#{number}", paper_id="p", section="s", paragraph=number, text=f"texto {number}")


def test_saved_index_comes_back_with_each_vector_on_its_chunk(tmp_path: Path) -> None:
    # A linha i da matriz é o embedding do pedaço i; fora de ordem, a busca devolveria o texto errado
    # para o vetor certo.
    index = EmbeddingIndex(
        model="modelo", max_words=200, chunks=[_chunk(0), _chunk(1)], vectors=np.eye(2, 3, dtype=np.float32)
    )

    save_index(index, tmp_path)
    loaded = load_index(tmp_path)

    assert loaded.chunks == index.chunks
    assert np.array_equal(loaded.vectors, index.vectors)
    assert (loaded.model, loaded.max_words) == ("modelo", 200)


def test_index_with_more_vectors_than_chunks_is_rejected() -> None:
    with pytest.raises(ValueError, match="2 pedaços e 3 vetores"):
        EmbeddingIndex(model="m", max_words=200, chunks=[_chunk(0), _chunk(1)], vectors=np.eye(3, dtype=np.float32))
