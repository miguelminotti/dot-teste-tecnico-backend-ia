"""Testes do value object PublicationDate: data de publicação como dia do calendário."""

from datetime import date, datetime

import pytest

from library.domain.errors import InvalidPublicationDateError
from library.domain.publication_date import PublicationDate

RELEASE_DAY = date(2026, 10, 28)


@pytest.mark.parametrize(
    ("as_of", "expected"),
    [
        (date(2026, 10, 27), False),
        (RELEASE_DAY, True),
        (date(2026, 10, 29), True),
    ],
    ids=["vespera", "dia-do-lancamento", "dia-seguinte"],
)
def test_is_published_compares_release_day_with_reference_day(as_of: date, expected: bool) -> None:
    # O dia do lançamento já conta como publicado; um erro de "<" por "<=" aqui deixaria
    # o livro um dia inteiro fora do catálogo publicado.
    assert PublicationDate(RELEASE_DAY).is_published(as_of=as_of) is expected


def test_accepts_future_date_for_pre_registration() -> None:
    # Pré-cadastro de lançamentos é regra de negócio: data futura não pode ser recusada.
    far_future = PublicationDate(date(2099, 1, 1))

    assert far_future.is_published(as_of=date(2026, 10, 27)) is False


def test_rejects_datetime_as_publication_date() -> None:
    # `datetime` é subclasse de `date` e passaria pelo mypy; com hora e fuso, a data de
    # publicação poderia mudar de dia conforme o fuso de quem consulta.
    with pytest.raises(InvalidPublicationDateError):
        PublicationDate(datetime(2026, 10, 28, 0, 0))


def test_is_published_rejects_instant_as_reference_day() -> None:
    # Trava a decisão de não aceitar instante como "hoje": o dia de referência é escolhido
    # por quem chama, no fuso que importa. O próprio Python recusa comparar date com datetime;
    # se alguém "consertar" isso convertendo o instante, o teste avisa.
    with pytest.raises(TypeError):
        PublicationDate(RELEASE_DAY).is_published(as_of=datetime(2026, 10, 28, 1, 0))
