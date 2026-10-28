"""Busca semântica: a consulta em texto vira embedding, e a busca devolve os artigos mais relevantes.

Uso, na pasta da questão, depois do semantic-search-embed e do semantic-search-store:
uv run semantic-search "como avaliar agentes de programação" --k 5
"""

import argparse
import io
import sys
import textwrap
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from sentence_transformers import SentenceTransformer

from semantic_search.chunking import Chunk
from semantic_search.corpus import Document, load_documents
from semantic_search.embeddings import Vectors, embed_queries, index_folder, load_model
from semantic_search.vector_store import VectorStore

# Pedaços buscados por artigo pedido, na primeira tentativa. Um artigo tem em média 54 pedaços, e os mais
# parecidos com a consulta tendem a vir de poucos artigos; quando não chegam a `k` artigos, a busca dobra.
_CHUNKS_PER_PAPER = 10


@dataclass(frozen=True, slots=True, kw_only=True)
class PaperResult:
    """Um artigo encontrado: a nota é a do pedaço mais parecido com a consulta, que é o trecho mostrado."""

    paper_id: str
    title: str
    url: str
    score: float
    excerpt: Chunk


def rank_papers(store: VectorStore, query: Vectors, *, k: int, documents: Mapping[str, Document]) -> list[PaperResult]:
    """Os `k` artigos mais relevantes para a consulta (um vetor), do mais para o menos relevante.

    Cada artigo vale pelo melhor pedaço. O resultado é exato: um artigo que não aparece entre os `n`
    pedaços buscados tem todos os pedaços abaixo do último deles, e portanto abaixo de cada artigo achado.
    """
    n = k * _CHUNKS_PER_PAPER
    while True:
        best: dict[str, PaperResult] = {}
        for hit in store.search(query, min(n, len(store)))[0]:
            # Os pedaços vêm do mais para o menos parecido: o primeiro de cada artigo é o melhor dele.
            if hit.chunk.paper_id not in best:
                document = documents[hit.chunk.paper_id]
                best[hit.chunk.paper_id] = PaperResult(
                    paper_id=document.id, title=document.title, url=document.url, score=hit.score, excerpt=hit.chunk
                )
        if len(best) >= k or n >= len(store):
            return list(best.values())[:k]
        n *= 2


class SemanticSearch:
    """A busca por texto: o modelo de embeddings, o índice FAISS e os artigos do corpus."""

    def __init__(self, model: SentenceTransformer, store: VectorStore, documents: Sequence[Document]) -> None:
        self._model = model
        self._store = store
        self._documents = {document.id: document for document in documents}

    @classmethod
    def load(cls, model_name: str, *, index: Path, corpus: Path) -> "SemanticSearch":
        store = VectorStore.load(index_folder(index, model_name))
        return cls(load_model(model_name), store, load_documents(corpus))

    def search(self, query: str, k: int = 5) -> list[PaperResult]:
        return rank_papers(self._store, embed_queries(self._model, [query]), k=k, documents=self._documents)


def format_results(results: Sequence[PaperResult]) -> str:
    """Os resultados para o terminal: posição, nota, título, link e o trecho, com a seção de onde veio."""
    lines = []
    for position, result in enumerate(results, start=1):
        excerpt = textwrap.shorten(result.excerpt.text, width=300, placeholder=" [...]")
        lines += [
            f"{position}. [{result.score:.3f}] {result.title}",
            f"   {result.url}",
            textwrap.fill(
                f"{result.excerpt.section}: {excerpt}", width=100, initial_indent="   ", subsequent_indent="   "
            ),
            "",
        ]
    return "\n".join(lines)


def print_results(results: Sequence[PaperResult]) -> None:
    """Imprime em UTF-8: redirecionada para arquivo, a saída do Python no Windows usa o cp1252, que não tem
    caracteres que aparecem nos artigos ("≥", letras gregas)."""
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    print(format_results(results))


def main() -> None:
    parser = argparse.ArgumentParser(description="Busca os artigos mais relevantes para uma consulta.")
    parser.add_argument("query", help="a consulta, em inglês ou português")
    parser.add_argument("--k", type=int, default=5, help="quantos artigos devolver")
    parser.add_argument("--model", default="intfloat/multilingual-e5-base", help="modelo dos embeddings")
    parser.add_argument("--index", type=Path, default=Path("data/index"))
    parser.add_argument("--corpus", type=Path, default=Path("data/corpus.jsonl"))
    args = parser.parse_args()

    search = SemanticSearch.load(args.model, index=args.index, corpus=args.corpus)
    print_results(search.search(args.query, k=args.k))
