"""Testes do repositório SQLite contra um banco real.

Nada de fake ou mock do banco: os testes que só usam uma conexão rodam num SQLite em memória, e os
que precisam de mais de uma conexão (persistência, concorrência) usam um arquivo temporário. O que
está em teste é justamente o comportamento do banco: transação, constraint, ordenação, LIKE.

Uma conexão `sqlite3` usada como context manager controla a transação, mas não fecha a conexão;
por isso os testes usam `contextlib.closing` quando precisam fechar.
"""

import sqlite3
import threading
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import pytest

from library.domain.book import Book
from library.domain.errors import BookAlreadyExistsError
from library.domain.publication_date import PublicationDate
from library.infrastructure.database import connect, create_schema
from library.infrastructure.sqlite_book_repository import SqliteBookRepository

SAO_PAULO = timezone(timedelta(hours=-3))
MakeBook = Callable[..., Book]
# Página maior que qualquer acervo montado nestes testes.
LIMIT = 100


@pytest.fixture
def connection() -> Iterator[sqlite3.Connection]:
    with closing(connect(":memory:")) as conn:
        create_schema(conn)
        yield conn


@pytest.fixture
def repository(connection: sqlite3.Connection) -> SqliteBookRepository:
    return SqliteBookRepository(connection)


@pytest.fixture
def database_file(tmp_path: Path) -> Path:
    path = tmp_path / "library.db"
    with closing(connect(path)) as conn:
        create_schema(conn)
    return path


def _titles(books: list[Book]) -> list[str]:
    return [book.title for book in books]


# --- Persistência e atomicidade ------------------------------------------------------------------


def test_added_book_survives_closing_the_connection(database_file: Path, make_book: MakeBook) -> None:
    # Sem commit, o insert fica numa transação aberta e some quando a conexão fecha: a API
    # responderia "cadastrado" e o livro não existiria.
    book = make_book()
    with closing(connect(database_file)) as writer:
        SqliteBookRepository(writer).add(book)

    with closing(connect(database_file)) as reader:
        assert [found.id for found in SqliteBookRepository(reader).search(limit=LIMIT)] == [book.id]


def test_round_trip_preserves_every_field(repository: SqliteBookRepository, make_book: MakeBook) -> None:
    # `Book.__eq__` compara só o id, então cada campo é conferido à parte. Data futura e horário
    # de São Paulo entram de propósito: são os dois valores que uma conversão errada deslocaria.
    original = make_book(
        publication_date=PublicationDate(date(2099, 1, 1)),
        created_at=datetime(2026, 10, 27, 22, 0, 0, 123456, tzinfo=SAO_PAULO),
    )
    repository.add(original)

    [loaded] = repository.search(limit=LIMIT)

    assert (loaded.id, loaded.title, loaded.author, loaded.summary) == (
        original.id,
        original.title,
        original.author,
        original.summary,
    )
    assert loaded.publication_date == original.publication_date
    assert loaded.created_at == original.created_at
    assert loaded.created_at.utcoffset() == timedelta(0)


def test_dates_are_stored_as_utc_and_calendar_day_text(
    repository: SqliteBookRepository, connection: sqlite3.Connection, make_book: MakeBook
) -> None:
    # O formato gravado é contrato do banco (ADR 0003): instante em UTC com offset explícito e
    # largura fixa (microssegundos mesmo quando zero, para o texto ordenar como o tempo), e data de
    # publicação como dia puro, sem hora.
    repository.add(
        make_book(
            publication_date=PublicationDate(date(2099, 1, 1)),
            created_at=datetime(2026, 10, 27, 22, 0, tzinfo=SAO_PAULO),
        )
    )

    row = connection.execute("SELECT publication_date, created_at FROM books").fetchone()

    assert (row["publication_date"], row["created_at"]) == ("2099-01-01", "2026-10-28T01:00:00.000000+00:00")


def test_duplicate_id_raises_domain_error_and_keeps_the_original(
    repository: SqliteBookRepository, make_book: MakeBook
) -> None:
    # Um `INSERT OR REPLACE` aqui sobrescreveria o livro existente em silêncio.
    original = make_book(title="Dom Casmurro")
    repository.add(original)

    with pytest.raises(BookAlreadyExistsError):
        repository.add(make_book(id=original.id, title="Outro título"))

    assert _titles(repository.search(limit=LIMIT)) == ["Dom Casmurro"]


def test_failed_add_does_not_leave_a_transaction_open(database_file: Path, make_book: MakeBook) -> None:
    # Se o erro deixasse a transação aberta, o próximo cadastro na mesma conexão ficaria preso
    # nela e se perderia ao fechar a conexão.
    first = make_book(title="Dom Casmurro")
    with closing(connect(database_file)) as conn:
        repository = SqliteBookRepository(conn)
        repository.add(first)
        with pytest.raises(BookAlreadyExistsError):
            repository.add(first)
        repository.add(make_book(title="Iracema"))

    with closing(connect(database_file)) as reader:
        assert _titles(SqliteBookRepository(reader).search(limit=LIMIT)) == ["Dom Casmurro", "Iracema"]


def test_concurrent_adds_of_the_same_book_persist_it_exactly_once(database_file: Path, make_book: MakeBook) -> None:
    # Race condition do tipo "check then act": se o repositório consultasse "já existe?" antes de
    # inserir, duas requisições simultâneas veriam "não" e as duas gravariam. A unicidade vem da
    # chave primária, checada pelo banco no próprio insert. Oito threads, cada uma com sua conexão,
    # tentam gravar o mesmo livro ao mesmo tempo (a barreira as solta juntas).
    book = make_book()
    attempts = 8
    barrier = threading.Barrier(attempts, timeout=5)

    def attempt(_: int) -> str:
        with closing(connect(database_file)) as conn:
            barrier.wait()
            try:
                SqliteBookRepository(conn).add(book)
            except BookAlreadyExistsError:
                return "duplicate"
            return "added"

    with ThreadPoolExecutor(max_workers=attempts) as pool:
        outcomes = list(pool.map(attempt, range(attempts)))

    assert sorted(outcomes) == ["added"] + ["duplicate"] * (attempts - 1)
    with closing(connect(database_file)) as reader:
        assert len(SqliteBookRepository(reader).search(limit=LIMIT)) == 1


def test_create_schema_twice_keeps_existing_books(
    repository: SqliteBookRepository, connection: sqlite3.Connection, make_book: MakeBook
) -> None:
    # O schema é criado a cada subida da aplicação; recriar a tabela apagaria o acervo.
    repository.add(make_book())

    create_schema(connection)

    assert len(repository.search(limit=LIMIT)) == 1


@pytest.mark.parametrize(
    ("publication_date", "created_at"),
    [
        ("2026-02-30", "2026-10-28T01:00:00.000000+00:00"),
        ("2026-10-28T00:00:00", "2026-10-28T01:00:00.000000+00:00"),
        ("2026-10-28", "2026-10-28T01:00:00.000000"),
        ("2026-10-28", "2026-10-27T22:00:00.000000-03:00"),
    ],
    ids=["dia-inexistente", "data-com-hora", "instante-sem-fuso", "instante-fora-de-utc"],
)
def test_database_rejects_dates_outside_the_policy(
    connection: sqlite3.Connection, publication_date: str, created_at: str
) -> None:
    # Os CHECKs valem para quem gravar sem passar pelo repositório (script, outra aplicação).
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        connection.execute(
            "INSERT INTO books VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("id", "titulo", "autor", "resumo", publication_date, created_at, "titulo", "autor"),
        )


# --- Busca ----------------------------------------------------------------------------------------


@pytest.fixture
def catalog(repository: SqliteBookRepository, make_book: MakeBook) -> SqliteBookRepository:
    for title, author in [
        ("Dom Casmurro", "Machado de Assis"),
        ("Iracema", "José de Alencar"),
        ("Incidente em Antares", "Érico Veríssimo"),
    ]:
        repository.add(make_book(title=title, author=author))
    return repository


@pytest.mark.parametrize(
    ("field", "query", "expected"),
    [
        ("author", "jose", ["Iracema"]),
        ("author", "JOSÉ DE", ["Iracema"]),
        # "É" maiúsculo fora do ASCII: o LIKE nativo do SQLite não o iguala a "é" nem a "e".
        ("author", "erico", ["Incidente em Antares"]),
        ("title", "INCIDENTE", ["Incidente em Antares"]),
        ("title", "casm", ["Dom Casmurro"]),
        ("author", "  assis  ", ["Dom Casmurro"]),
        ("title", "inexistente", []),
    ],
    ids=["sem-acento", "maiusculas-com-acento", "maiuscula-acentuada", "maiusculas", "trecho", "espacos", "nada"],
)
def test_search_ignores_case_and_accents(
    catalog: SqliteBookRepository, field: str, query: str, expected: list[str]
) -> None:
    # Livro que não aparece na busca é livro que não é encontrado nem emprestado.
    found = catalog.search(title=query, limit=LIMIT) if field == "title" else catalog.search(author=query, limit=LIMIT)

    assert _titles(found) == expected


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("%", ["100% Python"]),
        ("_", ["snake_case na prática"]),
        ("\\", ["C:\\livros"]),
    ],
    ids=["porcento", "sublinhado", "barra-invertida"],
)
def test_search_treats_like_wildcards_as_plain_text(
    catalog: SqliteBookRepository, make_book: MakeBook, query: str, expected: list[str]
) -> None:
    # Sem o escape, "%" casaria com o acervo inteiro e "_" com qualquer caractere.
    for title in ["100% Python", "snake_case na prática", "C:\\livros"]:
        catalog.add(make_book(title=title))

    assert _titles(catalog.search(title=query, limit=LIMIT)) == expected


def test_search_with_title_and_author_requires_both(catalog: SqliteBookRepository) -> None:
    assert _titles(catalog.search(title="dom", author="assis", limit=LIMIT)) == ["Dom Casmurro"]
    assert catalog.search(title="dom", author="alencar", limit=LIMIT) == []


def test_search_orders_alphabetically_ignoring_case_and_accents(
    repository: SqliteBookRepository, make_book: MakeBook
) -> None:
    # Ordenar pela coluna original poria "Ábaco" depois de "Abelha" (o "Á" vem depois do "z" em
    # bytes) e minúsculas depois de maiúsculas.
    for title in ["Abelha", "Ábaco", "abacate"]:
        repository.add(make_book(title=title))

    assert _titles(repository.search(limit=LIMIT)) == ["abacate", "Ábaco", "Abelha"]


def test_search_breaks_ties_by_id(repository: SqliteBookRepository, make_book: MakeBook) -> None:
    # Duas edições com mesmo título e autor: sem desempate, a ordem pode variar entre consultas,
    # e a paginação repetiria ou pularia livros.
    later_id = UUID("ffffffff-ffff-4fff-bfff-ffffffffffff")
    earlier_id = UUID("00000000-0000-4000-8000-000000000000")
    repository.add(make_book(id=later_id))
    repository.add(make_book(id=earlier_id))

    assert [book.id for book in repository.search(limit=LIMIT)] == [earlier_id, later_id]


# --- Paginação ------------------------------------------------------------------------------------


def test_search_returns_the_requested_slice_of_the_ordered_result(
    repository: SqliteBookRepository, make_book: MakeBook
) -> None:
    # `limit` e `offset` trocados, ou o OFFSET ignorado, devolveriam outra fatia sem erro nenhum.
    for title in ["E", "C", "A", "D", "B"]:
        repository.add(make_book(title=title))

    assert _titles(repository.search(limit=2, offset=1)) == ["B", "C"]


@pytest.mark.parametrize(
    ("limit", "offset"),
    [(0, 0), (-1, 0), (10, -1)],
    ids=["limit-zero", "limit-negativo", "offset-negativo"],
)
def test_search_rejects_pagination_that_sqlite_would_misread(
    repository: SqliteBookRepository, make_book: MakeBook, limit: int, offset: int
) -> None:
    # No SQLite, `LIMIT -1` é "sem limite": sem esta barreira, um limite negativo vindo de qualquer
    # porta de entrada devolveria o acervo inteiro.
    repository.add(make_book())

    with pytest.raises(ValueError, match="paginação inválida"):
        repository.search(limit=limit, offset=offset)
