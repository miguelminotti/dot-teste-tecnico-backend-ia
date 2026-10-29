"""Busca semântica: a consulta em texto vira embedding, e a busca devolve os artigos mais relevantes.

Uso, na pasta da questão (o índice do modelo padrão vem no repositório; com outro modelo, ou depois de mudar
o corpus, rode antes o semantic-search-embed e o semantic-search-store):
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
from semantic_search.embeddings import DEFAULT_MODEL, embed_queries, index_folder, load_model
from semantic_search.retrievers import BM25Retriever, DenseRetriever, HybridRetriever, Query, Retriever
from semantic_search.vector_store import VectorStore

METHODS = ("dense", "bm25", "hybrid")

# Pedaços buscados por artigo pedido, na primeira tentativa. Um artigo tem em média 50 pedaços, e os mais
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


def rank_papers(retriever: Retriever, query: Query, *, k: int, documents: Mapping[str, Document]) -> list[PaperResult]:
    """Os `k` artigos mais relevantes para a consulta, do mais para o menos relevante.

    Cada artigo vale pelo melhor pedaço. O resultado é exato: um artigo que não aparece entre os `n`
    pedaços buscados tem todos os pedaços abaixo do último deles, e portanto abaixo de cada artigo achado.
    Vêm menos de `k` quando o buscador acha pedaços de menos artigos, como o BM25 sem termo em comum.
    """
    if k < 1:
        raise ValueError(f"k precisa ser pelo menos 1, e veio {k}")
    n = k * _CHUNKS_PER_PAPER
    while True:
        best: dict[str, PaperResult] = {}
        for hit in retriever.search(query, min(n, len(retriever))):
            # Os pedaços vêm do mais para o menos relevante: o primeiro de cada artigo é o melhor dele.
            if hit.chunk.paper_id not in best:
                document = documents[hit.chunk.paper_id]
                best[hit.chunk.paper_id] = PaperResult(
                    paper_id=document.id, title=document.title, url=document.url, score=hit.score, excerpt=hit.chunk
                )
        if len(best) >= k or n >= len(retriever):
            return list(best.values())[:k]
        n *= 2


def load_retriever(method: str, folder: Path) -> Retriever:
    """O buscador de pedaços sobre o índice da pasta: "dense", "bm25" ou "hybrid" (os dois, pelo RRF)."""
    store = VectorStore.load(folder)
    dense = DenseRetriever(store)
    if method == "dense":
        return dense
    bm25 = BM25Retriever(store.chunks)
    return bm25 if method == "bm25" else HybridRetriever([dense, bm25])


class SemanticSearch:
    """A busca por texto: o modelo de embeddings, o buscador de pedaços e os artigos do corpus."""

    def __init__(self, model: SentenceTransformer, retriever: Retriever, documents: Sequence[Document]) -> None:
        self._model = model
        self._retriever = retriever
        self._documents = {document.id: document for document in documents}

    @classmethod
    def load(cls, model_name: str, *, index: Path, corpus: Path, method: str = "dense") -> "SemanticSearch":
        retriever = load_retriever(method, index_folder(index, model_name))
        return cls(load_model(model_name), retriever, load_documents(corpus))

    def search(self, query: str, k: int = 5) -> list[PaperResult]:
        if not query.strip():
            # A consulta em branco também vira um vetor, e a busca devolveria `k` artigos com nota alta.
            raise ValueError("a consulta veio em branco")
        vector = embed_queries(self._model, [query])
        return rank_papers(self._retriever, Query(text=query, vector=vector), k=k, documents=self._documents)


def format_results(results: Sequence[PaperResult]) -> str:
    """Os resultados para o terminal: posição, nota, título, link e o trecho, com a seção de onde veio."""
    if not results:
        return "Nenhum artigo encontrado."
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


def positive_int(value: str) -> int:
    """Tipo do argparse para `--k`: um inteiro a partir de 1, com mensagem de uso no lugar de um traceback."""
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError(f"precisa ser pelo menos 1, e veio {number}")
    return number


def query_text(value: str) -> str:
    """Tipo do argparse para a consulta: em branco, vira mensagem de uso antes de carregar o modelo.

    A mensagem vai para o stderr, que no Windows, redirecionado, sai em cp1252; sem acento, ela chega legível.
    """
    if not value.strip():
        raise argparse.ArgumentTypeError("a consulta veio em branco")
    return value


def use_utf8_output() -> None:
    """Passa a saída para UTF-8: redirecionada para arquivo, a saída do Python no Windows usa o cp1252, que
    não tem caracteres que aparecem nos artigos ("≥", letras gregas)."""
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")


def print_results(results: Sequence[PaperResult]) -> None:
    use_utf8_output()
    print(format_results(results))


def main() -> None:
    parser = argparse.ArgumentParser(description="Busca os artigos mais relevantes para uma consulta.")
    parser.add_argument("query", type=query_text, help="a consulta, em inglês ou português")
    parser.add_argument("--k", type=positive_int, default=5, help="quantos artigos devolver")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="modelo dos embeddings")
    parser.add_argument("--index", type=Path, default=Path("data/index"))
    parser.add_argument("--corpus", type=Path, default=Path("data/corpus.jsonl"))
    parser.add_argument("--method", choices=METHODS, default="dense", help="busca por embeddings, termos ou híbrida")
    args = parser.parse_args()

    search = SemanticSearch.load(args.model, index=args.index, corpus=args.corpus, method=args.method)
    print_results(search.search(args.query, k=args.k))
