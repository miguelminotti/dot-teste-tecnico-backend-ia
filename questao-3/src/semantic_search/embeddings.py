"""Geração dos embeddings: cada pedaço do corpus vira um vetor, gravado junto com o pedaço.

Uso, na pasta da questão: uv run semantic-search-embed (--model escolhe outro modelo)

O modelo roda localmente pelo sentence-transformers (sobre o transformers da Hugging Face), na CPU ou na
GPU que houver. Os vetores saem normalizados (norma 1): o produto interno entre eles é a similaridade de
cosseno, que é o que a vector store compara.
"""

import argparse
import json
import sys
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import numpy.typing as npt
from sentence_transformers import SentenceTransformer

from semantic_search.chunking import DEFAULT_MAX_WORDS, Chunk, chunk_documents
from semantic_search.corpus import load_documents

Vectors = npt.NDArray[np.float32]

# Modelo padrão de todos os comandos (docs/adr/0001-modelo-de-embeddings-bge-m3.md): o e5-base, mais leve,
# fica como opção com --model intfloat/multilingual-e5-base.
DEFAULT_MODEL = "BAAI/bge-m3"

# Prefixos que o modelo espera e que a configuração dele no sentence-transformers não traz. O e5 foi
# treinado com "query: " na consulta e "passage: " no documento; sem eles, consulta e documento saem com
# o mesmo embedding, e a busca perde qualidade sem nenhum erro aparente. Modelos que trazem os próprios
# prompts (como o Qwen3-Embedding) ficam fora da tabela.
_PROMPTS_BY_FAMILY = {"intfloat/multilingual-e5-": {"query": "query: ", "document": "passage: "}}


def prompts_for(model_name: str) -> dict[str, str] | None:
    """Prefixos de consulta e documento do modelo; None quando ele traz os próprios."""
    return next((prompts for family, prompts in _PROMPTS_BY_FAMILY.items() if model_name.startswith(family)), None)


def load_model(model_name: str) -> SentenceTransformer:
    return SentenceTransformer(model_name, prompts=prompts_for(model_name))


def embed_documents(model: SentenceTransformer, texts: Sequence[str], *, batch_size: int = 32) -> Vectors:
    vectors = model.encode_document(
        list(texts), batch_size=batch_size, normalize_embeddings=True, show_progress_bar=True, convert_to_numpy=True
    )
    return np.asarray(vectors, dtype=np.float32)


def embed_queries(model: SentenceTransformer, queries: Sequence[str]) -> Vectors:
    vectors = model.encode_query(list(queries), normalize_embeddings=True, convert_to_numpy=True)
    return np.asarray(vectors, dtype=np.float32)


@dataclass(frozen=True, slots=True, kw_only=True)
class EmbeddingIndex:
    """Os pedaços e os embeddings deles, na mesma ordem: a linha i de `vectors` é o pedaço i."""

    model: str
    max_words: int
    chunks: list[Chunk]
    vectors: Vectors

    def __post_init__(self) -> None:
        if len(self.chunks) != len(self.vectors):
            raise ValueError(f"{len(self.chunks)} pedaços e {len(self.vectors)} vetores: cada pedaço tem um vetor")


def save_index(index: EmbeddingIndex, folder: Path) -> None:
    """Grava os pedaços em JSONL, os vetores em .npy e o modelo e o corte em meta.json."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "chunks.jsonl").write_text(
        "".join(json.dumps(asdict(chunk), ensure_ascii=False) + "\n" for chunk in index.chunks), encoding="utf-8"
    )
    np.save(folder / "embeddings.npy", index.vectors)
    meta = {"model": index.model, "max_words": index.max_words, "chunks": len(index.chunks)}
    meta["dimensions"] = int(index.vectors.shape[1])
    (folder / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def load_index(folder: Path) -> EmbeddingIndex:
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    vectors = np.load(folder / "embeddings.npy").astype(np.float32, copy=False)
    return EmbeddingIndex(model=meta["model"], max_words=meta["max_words"], chunks=load_chunks(folder), vectors=vectors)


def load_chunks(folder: Path) -> list[Chunk]:
    """Só os pedaços do índice, sem a matriz de vetores: o que a busca precisa além do índice FAISS."""
    return [Chunk(**json.loads(line)) for line in (folder / "chunks.jsonl").read_text(encoding="utf-8").splitlines()]


def index_folder(root: Path, model_name: str) -> Path:
    """Pasta do índice de um modelo: um por modelo, para que a comparação entre eles não regere os outros."""
    return root / model_name.replace("/", "__")


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera os embeddings dos pedaços do corpus.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="modelo do sentence-transformers")
    parser.add_argument("--max-words", type=int, default=DEFAULT_MAX_WORDS, help="teto de palavras por pedaço")
    parser.add_argument("--corpus", type=Path, default=Path("data/corpus.jsonl"))
    parser.add_argument("--out", type=Path, default=Path("data/index"))
    args = parser.parse_args()

    chunks = chunk_documents(load_documents(args.corpus), max_words=args.max_words)
    model = load_model(args.model)
    started = time.perf_counter()
    vectors = embed_documents(model, [chunk.text for chunk in chunks])
    seconds = time.perf_counter() - started
    folder = index_folder(args.out, args.model)
    save_index(EmbeddingIndex(model=args.model, max_words=args.max_words, chunks=chunks, vectors=vectors), folder)
    print(f"{len(chunks)} pedaços, {vectors.shape[1]} dimensões, {seconds:.0f} s, em {folder}", file=sys.stderr)
