"""Testes do rate limiter com relógio controlado: o tempo avança por atribuição, sem `sleep`."""

import pytest

from library.api.rate_limit import FixedWindowRateLimiter


class FakeClock:
    def __init__(self, now: float = 0.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


def test_allows_up_to_the_limit_then_blocks_with_time_until_the_window_turns() -> None:
    # Um a mais que o limite e a proteção não existe; um a menos e o cliente legítimo é barrado.
    clock = FakeClock(now=100.0)
    limiter = FixedWindowRateLimiter(max_requests=3, window_seconds=60, clock=clock)

    assert [limiter.acquire("10.0.0.1") for _ in range(3)] == [None, None, None]

    clock.now = 115.0
    # A janela atual vai de 60 a 120: faltam 5 segundos para ela virar.
    assert limiter.acquire("10.0.0.1") == pytest.approx(5.0)


def test_limit_resets_when_the_window_turns() -> None:
    # Sem o reset, um cliente bloqueado uma vez ficaria bloqueado para sempre.
    clock = FakeClock(now=0.0)
    limiter = FixedWindowRateLimiter(max_requests=1, window_seconds=60, clock=clock)
    limiter.acquire("10.0.0.1")
    assert limiter.acquire("10.0.0.1") is not None

    clock.now = 60.0

    assert limiter.acquire("10.0.0.1") is None


def test_late_request_from_the_previous_window_does_not_reset_the_counters() -> None:
    # Bug: o relógio era lido fora do lock. Uma requisição que leu o tempo antes da virada e só
    # entrou no lock depois de outra da janela nova "voltava" a janela, zerava os contadores, e a
    # próxima requisição zerava de novo: o cliente ganhava requisições extras justo na virada.
    # O relógio que anda para trás simula essa ordem de chegada.
    clock = FakeClock(now=61.0)
    limiter = FixedWindowRateLimiter(max_requests=1, window_seconds=60, clock=clock)
    assert limiter.acquire("10.0.0.1") is None

    clock.now = 59.0
    limiter.acquire("10.0.0.2")
    clock.now = 62.0

    assert limiter.acquire("10.0.0.1") is not None


def test_each_client_has_its_own_limit() -> None:
    # Um contador compartilhado deixaria um cliente abusivo bloquear todos os outros
    # (o defeito encontrado no fastapi-limiter, ADR 0007).
    limiter = FixedWindowRateLimiter(max_requests=1, window_seconds=60, clock=FakeClock())
    limiter.acquire("10.0.0.1")

    assert limiter.acquire("10.0.0.1") is not None
    assert limiter.acquire("10.0.0.2") is None
