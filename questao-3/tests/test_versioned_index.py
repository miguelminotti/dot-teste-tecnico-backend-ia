import json
from pathlib import Path

from semantic_search.chunking import DEFAULT_MAX_WORDS, chunk_documents
from semantic_search.corpus import load_documents
from semantic_search.embeddings import DEFAULT_MODEL, load_chunks
from semantic_search.vector_store import VectorStore

DATA = Path(__file__).parents[1] / "data"
# A pasta que o .gitignore libera; as dos outros modelos ficam só na máquina de quem as gerou.
VERSIONED_INDEX = DATA / "index" / "BAAI__bge-m3"


def test_versioned_index_matches_the_corpus_and_the_default_model() -> None:
    # O índice do modelo padrão vem no git para que a busca rode sem indexar. Se o corpus, a divisão em
    # pedaços ou o modelo padrão mudarem sem regerar o índice, a busca devolveria trechos de pedaços que
    # não existem mais, sem nenhum erro.
    meta = json.loads((VERSIONED_INDEX / "meta.json").read_text(encoding="utf-8"))

    assert (meta["model"], meta["max_words"]) == (DEFAULT_MODEL, DEFAULT_MAX_WORDS)
    assert load_chunks(VERSIONED_INDEX) == chunk_documents(load_documents(DATA / "corpus.jsonl"))
    assert len(VectorStore.load(VERSIONED_INDEX)) == meta["chunks"]
