"""Limite de requisições por cliente, em janela fixa e em memória."""

import threading
import time
from collections.abc import Callable


class FixedWindowRateLimiter:
    """Permite até `max_requests` por cliente a cada janela de `window_seconds`.

    Janela fixa: o tempo é dividido em janelas (de 0 a 60s, de 60 a 120s...) e cada cliente tem um
    contador por janela. É o algoritmo mais simples que resolve o problema: num pior caso, um
    cliente faz o dobro do limite somando o fim de uma janela e o começo da seguinte, o que é
    aceitável para proteger a API contra laço e uso abusivo.

    O estado vive na memória do processo. Com vários workers, cada um conta o seu; para um limite
    compartilhado, o contador iria para um Redis. O relógio é injetável para os testes.
    """

    def __init__(self, *, max_requests: int, window_seconds: int, clock: Callable[[], float] = time.monotonic) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._clock = clock
        # cliente -> requisições feitas na janela atual
        self._counters: dict[str, int] = {}
        self._current_window = -1
        # As rotas síncronas do FastAPI rodam num pool de threads; o lock evita que duas
        # requisições do mesmo cliente leiam o mesmo contador e as duas passem.
        self._lock = threading.Lock()

    def acquire(self, client: str) -> float | None:
        """Registra uma requisição do cliente.

        Devolve `None` se ela está dentro do limite, ou quantos segundos faltam para a janela
        virar, se o limite estourou.
        """
        with self._lock:
            # O relógio é lido dentro do lock: lido fora, uma requisição atrasada da janela
            # anterior podia entrar depois de uma da janela nova e fazer a janela voltar.
            now = self._clock()
            window = int(now // self._window_seconds)
            if window > self._current_window:
                # Janela nova: os contadores antigos não valem mais. Descartá-los aqui mantém a
                # memória proporcional aos clientes ativos, não a todos que já passaram.
                self._counters.clear()
                self._current_window = window

            count = self._counters.get(client, 0)
            if count >= self._max_requests:
                return max((self._current_window + 1) * self._window_seconds - now, 0.0)
            self._counters[client] = count + 1
            return None
