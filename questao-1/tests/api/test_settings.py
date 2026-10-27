"""Testes da configuração: valor inválido para a subida com mensagem clara, não vira 500 depois."""

from typing import Any

import pytest

from library.api.settings import Settings


@pytest.mark.parametrize(
    "overrides",
    [{"rate_limit_window_seconds": 0}, {"rate_limit_window_seconds": -60}, {"rate_limit_requests": 0}],
    ids=["janela-zero", "janela-negativa", "zero-requisicoes"],
)
def test_rejects_rate_limit_values_that_break_or_block_the_api(overrides: dict[str, Any]) -> None:
    # Bug: janela zero fazia toda requisição dar 500 (divisão por zero no limiter), e zero
    # requisições bloqueava todo mundo com 429. Os dois só apareciam com a API já no ar.
    with pytest.raises(ValueError, match="LIBRARY_RATE_LIMIT"):
        Settings(**overrides)


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("LIBRARY_RATE_LIMIT_REQUESTS", "sessenta"),
        ("LIBRARY_RATE_LIMIT_WINDOW_SECONDS", "1.5"),
        ("LIBRARY_TIMEZONE", "America/Sao_Paul"),
    ],
    ids=["requisicoes-nao-numericas", "janela-fracionaria", "fuso-inexistente"],
)
def test_invalid_environment_variable_is_named_in_the_error(
    monkeypatch: pytest.MonkeyPatch, variable: str, value: str
) -> None:
    # Com "invalid literal for int()" ou um KeyError do zoneinfo, quem sobe a API não sabe qual
    # variável corrigir.
    monkeypatch.setenv(variable, value)

    with pytest.raises(ValueError, match=variable):
        Settings.from_env()
