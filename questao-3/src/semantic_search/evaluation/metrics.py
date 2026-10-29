"""Métricas de recuperação sobre uma lista ordenada de ids (artigos ou pedaços) e os ids relevantes.

Relevância binária: um id é relevante ou não. As mesmas funções medem a busca por artigo, com os artigos
rotulados pelo juiz, e por trecho, com os pedaços que contêm a citação de evidência.
"""

import math
from collections.abc import Collection, Sequence


def recall_at_k(ranked: Sequence[str], relevant: Collection[str], k: int) -> float:
    """Fração dos relevantes que aparece nos `k` primeiros: a cobertura da busca."""
    return len(set(ranked[:k]) & set(relevant)) / len(relevant)


def precision_at_k(ranked: Sequence[str], relevant: Collection[str], k: int) -> float:
    """Fração dos `k` primeiros que é relevante."""
    return len(set(ranked[:k]) & set(relevant)) / k


def reciprocal_rank(ranked: Sequence[str], relevant: Collection[str]) -> float:
    """1 sobre a posição do primeiro relevante; 0 se nenhum aparece. A média sobre as consultas é o MRR."""
    return next((1 / position for position, id_ in enumerate(ranked, start=1) if id_ in relevant), 0.0)


def ndcg_at_k(ranked: Sequence[str], relevant: Collection[str], k: int) -> float:
    """Ganho acumulado com desconto pela posição, dividido pelo da ordem ideal.

    A ordem ideal põe os relevantes primeiro, até `k`: com mais relevantes que `k`, a busca perfeita ainda
    tira 1.
    """
    dcg = sum(1 / math.log2(position + 1) for position, id_ in enumerate(ranked[:k], start=1) if id_ in relevant)
    ideal = sum(1 / math.log2(position + 1) for position in range(1, min(len(relevant), k) + 1))
    return dcg / ideal


def r_precision(ranked: Sequence[str], relevant: Collection[str]) -> float:
    """Precisão nas R primeiras posições, sendo R o número de relevantes: a busca perfeita tira 1 com
    qualquer número de relevantes, o que a precisão e a cobertura num `k` fixo não garantem."""
    return precision_at_k(ranked, relevant, len(relevant))


def contains_quote(text: str, quote: str) -> bool:
    """O pedaço contém a citação de evidência; só o espaço entre as palavras pode mudar."""
    normalized = " ".join(quote.split())
    return bool(normalized) and normalized in " ".join(text.split())
