"""Configuração da API, lida de variáveis de ambiente com padrões para rodar localmente."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo


@dataclass(frozen=True, slots=True, kw_only=True)
class Settings:
    """Configuração da aplicação.

    | Variável | Padrão |
    | --- | --- |
    | `LIBRARY_DATABASE_PATH` | `library.db` |
    | `LIBRARY_TIMEZONE` | `America/Sao_Paulo` |
    | `LIBRARY_RATE_LIMIT_REQUESTS` | `60` |
    | `LIBRARY_RATE_LIMIT_WINDOW_SECONDS` | `60` |
    """

    database_path: Path = Path("library.db")
    # Fuso em que a biblioteca opera: define o "hoje" de `is_published` (ADR 0005).
    timezone: ZoneInfo = field(default_factory=lambda: ZoneInfo("America/Sao_Paulo"))
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60

    @classmethod
    def from_env(cls) -> "Settings":
        defaults = cls()
        return cls(
            database_path=Path(os.environ.get("LIBRARY_DATABASE_PATH", defaults.database_path)),
            timezone=ZoneInfo(os.environ.get("LIBRARY_TIMEZONE", defaults.timezone.key)),
            rate_limit_requests=int(os.environ.get("LIBRARY_RATE_LIMIT_REQUESTS", defaults.rate_limit_requests)),
            rate_limit_window_seconds=int(
                os.environ.get("LIBRARY_RATE_LIMIT_WINDOW_SECONDS", defaults.rate_limit_window_seconds)
            ),
        )
