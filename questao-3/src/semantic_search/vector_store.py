"""Vector store: os embeddings dos pedaços num índice FAISS, consultado pelos vizinhos mais próximos.

Uso, na pasta da questão, depois do semantic-search-embed:
uv run semantic-search-store --model intfloat/multilingual-e5-base

O índice é o IndexFlatIP, a busca exata: compara a consulta com todos os vetores pelo produto interno, que,
com vetores de norma 1, é a similaridade de cosseno.
"""

import argparse
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np

from semantic_search.chunking import Chunk
from semantic_search.embeddings import EmbeddingIndex, Vectors, index_folder, load_index

_FAISS_FILE = "faiss.index"


@dataclass(frozen=True, slots=True, kw_only=True)
class Hit:
    """Um pedaço encontrado e a similaridade de cosseno dele com a consulta."""

    chunk: Chunk
    score: float


class VectorStore:
    """O índice FAISS e os pedaços na mesma ordem: o vetor i do índice é o pedaço i."""

    def __init__(self, faiss_index: faiss.Index, chunks: Sequence[Chunk]) -> None:
        if faiss_index.ntotal != len(chunks):
            raise ValueError(f"{faiss_index.ntotal} vetores e {len(chunks)} pedaços: cada pedaço tem um vetor")
        self._faiss_index = faiss_index
        self._chunks = list(chunks)

    def __len__(self) -> int:
        return len(self._chunks)

    @property
    def chunks(self) -> list[Chunk]:
        return list(self._chunks)

    @classmethod
    def build(cls, index: EmbeddingIndex) -> "VectorStore":
        norms = np.linalg.norm(index.vectors, axis=1)
        if not np.allclose(norms, 1.0, atol=1e-4):
            raise ValueError("os vetores precisam de norma 1 para que o produto interno seja o cosseno")
        faiss_index = faiss.IndexFlatIP(index.vectors.shape[1])
        faiss_index.add(index.vectors)
        return cls(faiss_index, index.chunks)

    def search(self, queries: Vectors, k: int) -> list[list[Hit]]:
        """Os `k` pedaços mais parecidos com cada consulta, do mais para o menos parecido."""
        scores, ids = self._faiss_index.search(queries, k)
        # Com menos de `k` vetores no índice, o FAISS completa as vagas com o id -1.
        return [
            [
                Hit(chunk=self._chunks[i], score=float(score))
                for i, score in zip(row_ids, row_scores, strict=True)
                if i >= 0
            ]
            for row_ids, row_scores in zip(ids, scores, strict=True)
        ]

    def save(self, folder: Path) -> None:
        """Grava só o índice FAISS; os pedaços ficam no chunks.jsonl da mesma pasta, gravado pelo save_index."""
        faiss.write_index(self._faiss_index, str(folder / _FAISS_FILE))

    @classmethod
    def load(cls, folder: Path) -> "VectorStore":
        return cls(faiss.read_index(str(folder / _FAISS_FILE)), load_index(folder).chunks)


def main() -> None:
    parser = argparse.ArgumentParser(description="Monta o índice FAISS a partir dos embeddings gravados.")
    parser.add_argument("--model", default="intfloat/multilingual-e5-base", help="modelo dos embeddings")
    parser.add_argument("--index", type=Path, default=Path("data/index"))
    args = parser.parse_args()

    folder = index_folder(args.index, args.model)
    started = time.perf_counter()
    store = VectorStore.build(load_index(folder))
    seconds = time.perf_counter() - started
    store.save(folder)
    size = (folder / _FAISS_FILE).stat().st_size
    print(f"índice montado em {seconds:.2f} s, {size / 1e6:.1f} MB, em {folder / _FAISS_FILE}", file=sys.stderr)
