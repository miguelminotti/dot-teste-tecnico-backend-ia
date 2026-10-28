import pytest
from langchain_core.messages import AIMessage

from chatbot.evaluation.usage import (
    WEB_SEARCH_CALL_USD,
    Price,
    TurnUsage,
    cache_hit_rate,
    measure_turn,
    percentile,
    price_of,
    turn_cost,
)

GPT_4_1_MINI = Price(input=0.40, cached_input=0.10, output=1.60)


def _turn(
    *, input_tokens: int, cache_read_tokens: int = 0, output_tokens: int = 0, web_search_calls: int = 0
) -> TurnUsage:
    return TurnUsage(
        input_tokens=input_tokens,
        cache_read_tokens=cache_read_tokens,
        output_tokens=output_tokens,
        web_search_calls=web_search_calls,
        latency_seconds=1.0,
    )


def test_cost_charges_cached_tokens_at_the_cache_price() -> None:
    # Números do quinto turno da conversa real, conferidos com o custo que o LangSmith registrou
    # (US$ 0,000445). Cobrar o cache pelo preço cheio quadruplicaria a entrada desse turno.
    usage = _turn(input_tokens=2332, cache_read_tokens=2176, output_tokens=103)

    assert turn_cost(usage, GPT_4_1_MINI) == pytest.approx(0.0004448)


def test_search_call_is_charged_on_top_of_the_tokens() -> None:
    # Os tokens das páginas buscadas já vêm no uso da resposta; a chamada da busca é cobrada à parte, e
    # sem ela o braço com busca sairia mais barato do que é.
    without_search = _turn(input_tokens=8474, output_tokens=151)
    with_search = _turn(input_tokens=8474, output_tokens=151, web_search_calls=2)

    assert turn_cost(with_search, GPT_4_1_MINI) == pytest.approx(
        turn_cost(without_search, GPT_4_1_MINI) + 2 * WEB_SEARCH_CALL_USD
    )


def test_turn_measure_adds_every_response_and_counts_the_searches() -> None:
    # Formato real da Responses API: cada busca é um bloco `web_search_call` no conteúdo da resposta.
    responses = [
        AIMessage(
            [
                {"type": "web_search_call", "id": "ws_1", "status": "completed"},
                {"type": "web_search_call", "id": "ws_2", "status": "completed"},
                {"type": "text", "text": "resposta"},
            ],
            usage_metadata={
                "input_tokens": 8474,
                "output_tokens": 151,
                "total_tokens": 8625,
                "input_token_details": {"cache_read": 1024},
            },
        ),
        AIMessage("outra", usage_metadata={"input_tokens": 100, "output_tokens": 10, "total_tokens": 110}),
    ]

    assert measure_turn(responses, latency_seconds=2.5) == TurnUsage(
        input_tokens=8574, cache_read_tokens=1024, output_tokens=161, web_search_calls=2, latency_seconds=2.5
    )


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
