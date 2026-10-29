import pytest

from semantic_search.chunking import Chunk
from semantic_search.evaluation.retrieval import EvalQuery, QueryResult, score_query, summarize


def _query(type_: str, relevant: tuple[str, ...] = ("a",), quote: str | None = None) -> EvalQuery:
    return EvalQuery(id="q", type=type_, text={"en": "query", "pt": "consulta"}, relevant=relevant, quote=quote)


def _chunk(number: int, text: str) -> Chunk:
    return Chunk(id=f"a#{number}", paper_id="a", section="s", paragraph=number, text=text)


def test_detail_queries_are_also_scored_by_the_chunk_that_contains_the_quote() -> None:
    query = _query("detail", quote="frase citada")
    chunks = [_chunk(0, "outro parágrafo"), _chunk(1, "aqui está a frase citada.")]

    scores = score_query(query, papers=["a", "x"], chunks=chunks, k=2)

    assert scores["chunk_mrr"] == pytest.approx(1 / 2)
    assert scores["chunk_recall"] == pytest.approx(1.0)


def test_queries_without_evidence_have_no_chunk_scores() -> None:
    scores = score_query(_query("named"), papers=["a", "x"], chunks=[_chunk(0, "texto")], k=2)

    assert not any(metric.startswith("chunk_") for metric in scores)


def test_paper_ranking_shorter_than_the_relevant_list_is_rejected() -> None:
    # A R-precision olha as R primeiras posições: com 3 relevantes e só 2 artigos buscados, sairia errada.
    query = _query("topic", relevant=("a", "b", "c"))

    with pytest.raises(ValueError, match="3 artigos"):
        score_query(query, papers=["a", "b"], chunks=[], k=2)


def test_paper_mrr_only_looks_at_the_top_k_like_the_other_metrics() -> None:
    # A lista passa de k quando há mais relevantes que k (para a R-precision); o 1º relevante em 3º, com k=2,
    # não conta, ou o MRR dependeria de quantos artigos vieram.
    query = _query("topic", relevant=("a", "b", "c"))

    scores = score_query(query, papers=["x", "y", "a"], chunks=[], k=2)

    assert scores["mrr"] == 0.0


def test_summary_averages_each_group_over_the_queries_that_have_the_metric() -> None:
    results = [
        QueryResult(query_id="q1", type="named", language="en", scores={"recall": 1.0}),
        QueryResult(query_id="q1", type="named", language="pt", scores={"recall": 0.0}),
        QueryResult(query_id="q2", type="detail", language="en", scores={"recall": 0.5, "chunk_recall": 1.0}),
    ]

    summary = summarize(results)

    assert summary[("named", "all")]["recall"] == pytest.approx(0.5)
    assert summary[("all", "en")]["recall"] == pytest.approx(0.75)
    assert summary[("all", "all")]["recall"] == pytest.approx(0.5)
    # Só as consultas de detalhe têm trecho de evidência: a média por trecho não conta as outras como zero.
    assert summary[("all", "all")]["chunk_recall"] == pytest.approx(1.0)
    assert ("named", "all") in summary and "chunk_recall" not in summary[("named", "all")]
