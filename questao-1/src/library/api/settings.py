"""Configuração da API, lida de variáveis de ambiente com padrões para rodar localmente."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass(frozen=True, slots=True, kw_only=True)
class Settings:
    """Configuração da aplicação; as variáveis e seus padrões estão documentados no `.env.example`.

    Valor inválido é recusado na construção, com o nome da variável na mensagem: a API não sobe,
    em vez de subir e responder 500 (ou 429 para todo mundo) na primeira requisição.
    """

    database_path: Path = Path("library.db")
    # Fuso em que a biblioteca opera: define o "hoje" de `is_published` (ADR 0003).
    timezone: ZoneInfo = field(default_factory=lambda: ZoneInfo("America/Sao_Paulo"))
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60

    def __post_init__(self) -> None:
        if self.rate_limit_requests < 1:
            raise ValueError("LIBRARY_RATE_LIMIT_REQUESTS deve ser pelo menos 1")
        # Janela zero dividiria por zero no rate limiter, a cada requisição.
        if self.rate_limit_window_seconds < 1:
            raise ValueError("LIBRARY_RATE_LIMIT_WINDOW_SECONDS deve ser pelo menos 1")

    @classmethod
    def from_env(cls) -> "Settings":
        defaults = cls()
        return cls(
            database_path=Path(os.environ.get("LIBRARY_DATABASE_PATH", defaults.database_path)),
            timezone=_timezone_env("LIBRARY_TIMEZONE", defaults.timezone),
            rate_limit_requests=_int_env("LIBRARY_RATE_LIMIT_REQUESTS", defaults.rate_limit_requests),
            rate_limit_window_seconds=_int_env("LIBRARY_RATE_LIMIT_WINDOW_SECONDS", defaults.rate_limit_window_seconds),
        )


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"{name} deve ser um número inteiro, veio {raw!r}") from None


def _timezone_env(name: str, default: ZoneInfo) -> ZoneInfo:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return ZoneInfo(raw)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError(f"{name} deve ser um fuso IANA, como America/Sao_Paulo; veio {raw!r}") from None
