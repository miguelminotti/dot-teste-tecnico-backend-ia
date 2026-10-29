import math

import pytest

from semantic_search.evaluation.metrics import (
    contains_quote,
    ndcg_at_k,
    precision_at_k,
    r_precision,
    recall_at_k,
    reciprocal_rank,
)


def test_recall_counts_the_relevant_papers_found_in_the_top_k() -> None:
    # c é relevante, mas está na 4ª posição, fora dos 3 primeiros.
    assert recall_at_k(["a", "x", "b", "c"], {"a", "b", "c", "d"}, k=3) == pytest.approx(2 / 4)


def test_precision_counts_the_relevant_share_of_the_top_k() -> None:
    assert precision_at_k(["a", "x", "b"], {"a", "b"}, k=2) == pytest.approx(1 / 2)


def test_reciprocal_rank_is_one_over_the_position_of_the_first_relevant() -> None:
    assert reciprocal_rank(["x", "a", "b"], {"a", "b"}) == pytest.approx(1 / 2)
    assert reciprocal_rank(["x", "y"], {"a"}) == 0.0


def test_ndcg_rewards_relevant_papers_higher_in_the_ranking() -> None:
    assert ndcg_at_k(["a", "x"], {"a"}, k=2) == pytest.approx(1.0)
    assert ndcg_at_k(["x", "a"], {"a"}, k=2) == pytest.approx(1 / math.log2(3))


def test_ndcg_of_a_perfect_ranking_is_one_even_with_more_relevant_papers_than_k() -> None:
    # Os temas largos têm até 18 relevantes: a busca perfeita enche os k primeiros e não pode perder nota.
    assert ndcg_at_k(["a", "b", "c"], {"a", "b", "c", "d", "e"}, k=3) == pytest.approx(1.0)


def test_r_precision_is_the_precision_at_the_number_of_relevant_papers() -> None:
    # Com 3 relevantes, olha os 3 primeiros: a busca perfeita tira 1 com qualquer número de relevantes.
    assert r_precision(["a", "x", "b", "c"], {"a", "b", "c"}) == pytest.approx(2 / 3)


def test_quote_is_found_in_a_chunk_regardless_of_whitespace() -> None:
    # A citação foi copiada do parágrafo; só o espaço entre as palavras pode mudar, como na geração.
    assert contains_quote("Usamos a  frase\n citada aqui.", "frase citada")
    assert not contains_quote("Usamos a frase citada aqui.", "frase não citada")
