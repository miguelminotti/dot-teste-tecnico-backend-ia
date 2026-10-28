import pytest

from chatbot.evaluation.usage import Price, TurnUsage, cache_hit_rate, percentile, price_of, turn_cost

GPT_4_1_MINI = Price(input=0.40, cached_input=0.10, output=1.60)


def _turn(*, input_tokens: int, cache_read_tokens: int = 0, output_tokens: int = 0) -> TurnUsage:
    return TurnUsage(
        input_tokens=input_tokens,
        cache_read_tokens=cache_read_tokens,
        output_tokens=output_tokens,
        latency_seconds=1.0,
    )


def test_cost_charges_cached_tokens_at_the_cache_price() -> None:
    # Números do quinto turno da conversa real, conferidos com o custo que o LangSmith registrou
    # (US$ 0,000445). Cobrar o cache pelo preço cheio quadruplicaria a entrada desse turno.
    usage = _turn(input_tokens=2332, cache_read_tokens=2176, output_tokens=103)

    assert turn_cost(usage, GPT_4_1_MINI) == pytest.approx(0.0004448)


def test_model_without_price_is_an_error_not_free() -> None:
    # Custo zero para um modelo novo faria o experimento parecer de graça e ganhar na comparação.
    with pytest.raises(ValueError, match="gpt-novo"):
        price_of("gpt-novo")


def test_cache_hit_rate_is_weighted_by_tokens() -> None:
    # A média das taxas por turno daria 50%; pelo custo, só 2.000 de 2.100 tokens saíram do cache.
    turns = [_turn(input_tokens=100), _turn(input_tokens=2000, cache_read_tokens=2000)]

    assert cache_hit_rate(turns) == pytest.approx(2000 / 2100)


def test_cache_hit_rate_without_input_is_undefined() -> None:
    assert cache_hit_rate([]) is None


def test_percentile_returns_values_that_occurred() -> None:
    latencies = [1.0, 2.0, 3.0, 4.0, 10.0]

    assert percentile(latencies, 0.5) == 3.0
    assert percentile(latencies, 0.95) == 10.0
