"""Métricas de uso de cada turno: custo, taxa de acerto do cache e latência."""

import math
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class TurnUsage:
    """O que um turno consumiu, medido em volta da chamada ao `Tutor`."""

    input_tokens: int
    # Parte dos tokens de entrada lida do cache de prompt, cobrada com desconto.
    cache_read_tokens: int
    output_tokens: int
    latency_seconds: float


@dataclass(frozen=True, slots=True, kw_only=True)
class Price:
    """Preço em US$ por milhão de tokens."""

    input: float
    cached_input: float
    output: float


# Tabela de preços da OpenAI, camada padrão, consultada em 2026-10-28. Só os modelos candidatos: um
# modelo fora da tabela é erro, e não custo zero, para que o experimento não saia barato por engano.
PRICES: dict[str, Price] = {
    "gpt-4.1": Price(input=2.00, cached_input=0.50, output=8.00),
    "gpt-4.1-mini": Price(input=0.40, cached_input=0.10, output=1.60),
    "gpt-4.1-nano": Price(input=0.10, cached_input=0.025, output=0.40),
    "gpt-5-mini": Price(input=0.25, cached_input=0.025, output=2.00),
    "gpt-5.4-mini": Price(input=0.75, cached_input=0.075, output=4.50),
    "gpt-5.4-nano": Price(input=0.20, cached_input=0.02, output=1.25),
}


def price_of(model: str) -> Price:
    try:
        return PRICES[model]
    except KeyError:
        raise ValueError(f"sem preço para o modelo {model!r}: acrescente em PRICES") from None


def turn_cost(usage: TurnUsage, price: Price) -> float:
    """Custo do turno em US$, com os tokens lidos do cache pelo preço de cache."""
    uncached_input = usage.input_tokens - usage.cache_read_tokens
    return (
        uncached_input * price.input + usage.cache_read_tokens * price.cached_input + usage.output_tokens * price.output
    ) / 1_000_000


def cache_hit_rate(turns: Sequence[TurnUsage]) -> float | None:
    """Fração dos tokens de entrada lida do cache, somando os turnos.

    Ponderada por token, e não a média das taxas de cada turno: o que pesa no custo é quantos tokens
    saíram do cache, e um turno de 2.000 tokens importa mais que um de 100.
    """
    total = sum(turn.input_tokens for turn in turns)
    if total == 0:
        return None
    return sum(turn.cache_read_tokens for turn in turns) / total


def percentile(values: Sequence[float], fraction: float) -> float:
    """Percentil pelo método do posto mais próximo: sempre um valor que de fato ocorreu."""
    if not values:
        raise ValueError("percentil de uma lista vazia")
    ordered = sorted(values)
    return ordered[max(math.ceil(fraction * len(ordered)) - 1, 0)]
