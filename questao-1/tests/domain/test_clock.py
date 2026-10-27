"""Testes da política de tempo: todo instante do sistema vive em UTC.

Os fusos são offsets fixos (`timezone(timedelta(...))`) em vez de `ZoneInfo("America/Sao_Paulo")`:
o teste fica independente da base de fusos do sistema (que no Windows exige o pacote `tzdata`) e de
mudanças de horário de verão. O que está em teste é a conversão, não a base de fusos.
"""

from datetime import UTC, datetime, timedelta, timezone, tzinfo

import pytest

from library.domain.clock import to_utc, utc_now
from library.domain.errors import NotProvidedTimezoneError

SAO_PAULO = timezone(timedelta(hours=-3))
TOKYO = timezone(timedelta(hours=9))


def test_utc_now_returns_aware_instant_in_utc() -> None:
    # Se um dia alguém trocar por `datetime.now()` ou `datetime.utcnow()` (ambos sem fuso),
    # o horário local da máquina passaria a ser gravado como se fosse UTC.
    now = utc_now()

    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(0)


@pytest.mark.parametrize(
    ("local", "expected_utc"),
    [
        # 22h em São Paulo já é o dia seguinte em UTC.
        (datetime(2026, 10, 27, 22, 0, tzinfo=SAO_PAULO), datetime(2026, 10, 28, 1, 0, tzinfo=UTC)),
        # 8h em Tóquio ainda é o dia anterior em UTC.
        (datetime(2026, 10, 28, 8, 0, tzinfo=TOKYO), datetime(2026, 10, 27, 23, 0, tzinfo=UTC)),
        # Instante que já está em UTC não muda.
        (datetime(2026, 10, 27, 12, 0, tzinfo=UTC), datetime(2026, 10, 27, 12, 0, tzinfo=UTC)),
    ],
    ids=["sao-paulo-vira-o-dia", "tokyo-volta-o-dia", "utc-inalterado"],
)
def test_to_utc_converts_to_same_instant_in_utc(local: datetime, expected_utc: datetime) -> None:
    converted = to_utc(local)

    # Compara campo a campo (e não só `==`, que entre datetimes com fuso compara o instante
    # e passaria mesmo se o fuso não tivesse sido trocado para UTC).
    assert converted.utcoffset() == timedelta(0)
    assert (converted.date(), converted.time()) == (expected_utc.date(), expected_utc.time())


def test_to_utc_rejects_naive_instant() -> None:
    # Sem fuso não há como saber de onde é o "10:00"; adivinhar desloca o horário em silêncio.
    with pytest.raises(NotProvidedTimezoneError):
        to_utc(datetime(2026, 10, 27, 10, 0))


class _TimezoneWithoutOffset(tzinfo):
    """Fuso que existe mas não informa offset: o Python trata esse datetime como naive."""

    def utcoffset(self, dt: datetime | None) -> timedelta | None:
        return None

    def dst(self, dt: datetime | None) -> timedelta | None:
        return None

    def tzname(self, dt: datetime | None) -> str | None:
        return None


def test_to_utc_rejects_tzinfo_without_offset() -> None:
    # Checar só `tzinfo is None` deixaria esse caso passar, e o `astimezone` o converteria a
    # partir do fuso local da máquina, o mesmo erro silencioso do datetime naive.
    with pytest.raises(NotProvidedTimezoneError):
        to_utc(datetime(2026, 10, 27, 10, 0, tzinfo=_TimezoneWithoutOffset()))
