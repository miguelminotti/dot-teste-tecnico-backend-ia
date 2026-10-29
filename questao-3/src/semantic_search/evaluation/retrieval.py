"""Avaliação da recuperação: roda as consultas de avaliação na busca e mede o resultado.

Uso, na pasta da questão, depois do semantic-search-embed e do semantic-search-store:
uv run semantic-search-eval --model intfloat/multilingual-e5-base

Cada consulta roda nas duas línguas. A busca por artigo é medida em todas, contra os artigos rotulados pelo
juiz; a busca por trecho, só nas de detalhe, contra o pedaço que contém a citação de evidência. As médias
saem por tipo de consulta e por língua, porque cada tipo testa uma fraqueza diferente da busca.
"""

import argparse
import json
import sys
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from semantic_search.chunking import Chunk
from semantic_search.corpus import load_documents
from semantic_search.embeddings import embed_queries, index_folder, load_model
from semantic_search.evaluation.metrics import (
    contains_quote,
    ndcg_at_k,
    precision_at_k,
    r_precision,
    recall_at_k,
    reciprocal_rank,
)
from semantic_search.search import rank_papers, use_utf8_output
from semantic_search.vector_store import VectorStore

LANGUAGES = ("en", "pt")
TYPES = ("named", "paraphrase", "detail", "topic")
# Grupo que junta todos os tipos ou as duas línguas.
ALL = "all"


@dataclass(frozen=True, slots=True, kw_only=True)
class EvalQuery:
    """Uma consulta de avaliação: o texto em cada língua, os artigos relevantes e, nas de detalhe, a citação."""

    id: str
    type: str
    text: dict[str, str]
    relevant: tuple[str, ...]
    quote: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class QueryResult:
    """As notas de uma consulta numa língua, e os artigos que a busca devolveu, para a análise dos erros."""

    query_id: str
    type: str
    language: str
    scores: dict[str, float]
    papers: tuple[str, ...] = ()


def load_queries(path: Path) -> list[EvalQuery]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        EvalQuery(
            id=query["id"],
            type=query["type"],
            text=query["query"],
            relevant=tuple(query["relevant"]),
            quote=query["evidence"]["quote"] if query["evidence"] else None,
        )
        for query in data["queries"]
    ]


def score_query(query: EvalQuery, *, papers: Sequence[str], chunks: Sequence[Chunk], k: int) -> dict[str, float]:
    """As métricas de uma consulta: por artigo sobre `papers`, e por trecho sobre `chunks` (os `k` pedaços
    buscados) se houver citação.

    `papers` precisa de pelo menos max(k, R) artigos, sendo R o número de relevantes: a R-precision olha as
    R primeiras posições, e três temas têm mais relevantes que `k`. As outras métricas olham só os `k`
    primeiros, para que a nota não dependa de quantos artigos vieram.
    """
    needed = max(k, len(query.relevant))
    if len(papers) < needed:
        raise ValueError(f"a consulta {query.id} precisa de {needed} artigos na lista, e vieram {len(papers)}")
    relevant = set(query.relevant)
    scores = {
        "recall": recall_at_k(papers, relevant, k),
        "precision": precision_at_k(papers, relevant, k),
        "mrr": reciprocal_rank(papers[:k], relevant),
        "ndcg": ndcg_at_k(papers, relevant, k),
        "r_precision": r_precision(papers, relevant),
    }
    if query.quote is not None:
        ids = [chunk.id for chunk in chunks]
        evidence = {chunk.id for chunk in chunks if contains_quote(chunk.text, query.quote)}
        # Sem o pedaço de evidência entre os buscados, recall e MRR são 0; com ele, o conjunto não é vazio.
        scores["chunk_recall"] = 1.0 if evidence else 0.0
        scores["chunk_mrr"] = reciprocal_rank(ids, evidence)
    return scores


def summarize(results: Sequence[QueryResult]) -> dict[tuple[str, str], dict[str, float]]:
    """Média de cada métrica por (tipo, língua), com ALL juntando os tipos ou as línguas.

    Cada métrica é a média só das consultas que a têm: as métricas por trecho existem só nas de detalhe.
    """
    values: dict[tuple[str, str], dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for result in results:
        for group in _groups(result):
            for metric, value in result.scores.items():
                values[group][metric].append(value)
    return {
        group: {metric: sum(scores) / len(scores) for metric, scores in metrics.items()}
        for group, metrics in values.items()
    }


def count_queries(results: Sequence[QueryResult]) -> dict[tuple[str, str], int]:
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for result in results:
        for group in _groups(result):
            counts[group] += 1
    return counts


def _groups(result: QueryResult) -> list[tuple[str, str]]:
    """Os grupos em que a consulta entra: o tipo e a língua dela, cada um também junto com todos os outros."""
    return [(result.type, result.language), (result.type, ALL), (ALL, result.language), (ALL, ALL)]


def evaluate(
    store: VectorStore, model_name: str, queries: Sequence[EvalQuery], *, corpus: Path, k: int
) -> list[QueryResult]:
    """Roda cada consulta nas duas línguas e devolve as notas de cada uma."""
    documents = {document.id: document for document in load_documents(corpus)}
    pairs = [(query, language) for query in queries for language in LANGUAGES]
    vectors = embed_queries(load_model(model_name), [query.text[language] for query, language in pairs])
    results = []
    for (query, language), vector in zip(pairs, vectors, strict=True):
        papers = rank_papers(store, vector[None, :], k=max(k, len(query.relevant)), documents=documents)
        chunks = [hit.chunk for hit in store.search(vector[None, :], k)[0]]
        paper_ids = [paper.paper_id for paper in papers]
        results.append(
            QueryResult(
                query_id=query.id,
                type=query.type,
                language=language,
                scores=score_query(query, papers=paper_ids, chunks=chunks, k=k),
                papers=tuple(paper_ids[:k]),
            )
        )
    return results


def format_summary(summary: dict[tuple[str, str], dict[str, float]], counts: dict[tuple[str, str], int], k: int) -> str:
    """Tabela em Markdown: uma linha por tipo e língua, uma coluna por métrica."""
    metrics = [
        ("recall", f"Recall@{k}"),
        ("precision", f"P@{k}"),
        ("mrr", "MRR"),
        ("ndcg", f"NDCG@{k}"),
        ("r_precision", "R-prec."),
        ("chunk_recall", f"Trecho@{k}"),
        ("chunk_mrr", "MRR trecho"),
    ]
    lines = [
        "| Tipo | Língua | Consultas | " + " | ".join(label for _, label in metrics) + " |",
        "| --- | --- | ---: | " + " | ".join("---:" for _ in metrics) + " |",
    ]
    for type_ in (*TYPES, ALL):
        for language in (*LANGUAGES, ALL):
            group = summary[(type_, language)]
            cells = [f"{group[metric]:.3f}" if metric in group else "" for metric, _ in metrics]
            names = ("todos" if type_ == ALL else type_, "ambas" if language == ALL else language)
            lines.append(f"| {names[0]} | {names[1]} | {counts[(type_, language)]} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Mede a busca nas consultas de avaliação.")
    parser.add_argument("--model", default="intfloat/multilingual-e5-base", help="modelo dos embeddings")
    parser.add_argument("--k", type=int, default=10, help="posições avaliadas")
    parser.add_argument("--index", type=Path, default=Path("data/index"))
    parser.add_argument("--corpus", type=Path, default=Path("data/corpus.jsonl"))
    parser.add_argument("--queries", type=Path, default=Path("evals/queries.json"))
    parser.add_argument("--out", type=Path, default=Path("evals/results"))
    args = parser.parse_args()

    store = VectorStore.load(index_folder(args.index, args.model))
    results = evaluate(store, args.model, load_queries(args.queries), corpus=args.corpus, k=args.k)
    summary = summarize(results)
    counts = count_queries(results)

    report = {
        "model": args.model,
        "k": args.k,
        "summary": [
            {"type": type_, "language": language, "queries": counts[(type_, language)], **metrics}
            for (type_, language), metrics in sorted(summary.items())
        ],
        "results": [asdict(result) for result in results],
    }
    # Um arquivo por modelo, com o nome da pasta do índice: with_suffix cortaria "Qwen3-Embedding-0.6B" no ponto.
    out = args.out / f"{index_folder(args.out, args.model).name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    use_utf8_output()
    print(format_summary(summary, counts, args.k))
    print(f"\nresultados por consulta em {out}", file=sys.stderr)
