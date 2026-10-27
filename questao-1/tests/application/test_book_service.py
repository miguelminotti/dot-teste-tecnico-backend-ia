"""Testes do BookService: o "hoje" da biblioteca e como ele chega ao `is_published`.

O que a API já cobre de ponta a ponta (cadastro, validação, paginação) não se repete aqui. Estes
testes fixam o dia de referência, coisa que pela API dependeria do relógio real.
"""

import sqlite3
from collections.abc import Callable, Iterator
from contextlib import closing
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from library.application.book_service import BookService, today_in
from library.application.dtos import RegisterBookCommand
from library.infrastructure.database import connect, create_schema
from library.infrastructure.sqlite_book_repository import SqliteBookRepository

RELEASE_DAY = date(2026, 10, 28)


@pytest.fixture
def connection() -> Iterator[sqlite3.Connection]:
    with closing(connect(":memory:")) as conn:
        create_schema(conn)
        yield conn


def make_service(connection: sqlite3.Connection, today: Callable[[], date]) -> BookService:
    return BookService(SqliteBookRepository(connection), today=today)


def command(title: str = "Lançamento", publication_date: date = RELEASE_DAY) -> RegisterBookCommand:
    return RegisterBookCommand(title=title, author="Autora", publication_date=publication_date, summary="Resumo.")


@pytest.mark.parametrize(
    ("today", "expected"),
    [(date(2026, 10, 27), False), (RELEASE_DAY, True)],
    ids=["vespera", "dia-do-lancamento"],
)
def test_is_published_uses_the_library_day_given_to_the_service(
    connection: sqlite3.Connection, today: date, expected: bool
) -> None:
    # Se o serviço lesse o relógio por conta própria em vez do "hoje" que recebe, o fuso da
    # biblioteca seria ignorado e o lançamento poderia aparecer publicado antes da hora.
    service = make_service(connection, today=lambda: today)

    registered = service.register(command())
    [found] = service.search(limit=10).items

    assert (registered.is_published, found.is_published) == (expected, expected)


@pytest.mark.parametrize(
    ("timezone", "expected_day"),
    [
        # 01h UTC de 28/10 ainda é 22h de 27/10 em São Paulo.
        ("America/Sao_Paulo", date(2026, 10, 27)),
        # Em Tóquio já são 10h de 28/10.
        ("Asia/Tokyo", date(2026, 10, 28)),
    ],
    ids=["sao-paulo-ainda-e-ontem", "toquio-ja-e-hoje"],
)
def test_today_in_converts_the_utc_instant_to_the_library_day(
    monkeypatch: pytest.MonkeyPatch, timezone: str, expected_day: date
) -> None:
    # O "hoje" tirado direto do UTC adiantaria em três horas, em São Paulo, todo lançamento
    # marcado para o dia seguinte (ADR 0005).
    monkeypatch.setattr("library.application.book_service.utc_now", lambda: datetime(2026, 10, 28, 1, 0, tzinfo=UTC))

    assert today_in(ZoneInfo(timezone))() == expected_day


def test_all_books_in_a_page_share_the_same_day(connection: sqlite3.Connection) -> None:
    # Se a meia-noite passar enquanto a página é montada, livros com a mesma data de lançamento
    # não podem sair uns publicados e outros não na mesma resposta.
    days = iter([date(2026, 10, 27), RELEASE_DAY, RELEASE_DAY])
    registering = make_service(connection, today=lambda: RELEASE_DAY)
    registering.register(command(title="Primeiro"))
    registering.register(command(title="Segundo"))

    page = make_service(connection, today=lambda: next(days)).search(limit=10)

    assert [book.is_published for book in page.items] == [False, False]
