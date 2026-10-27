"""Testes da entidade Book: invariantes de cadastro e identidade."""

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta, timezone
from uuid import uuid4

import pytest

from library.domain.book import Book
from library.domain.errors import InvalidBookError
from library.domain.publication_date import PublicationDate

SAO_PAULO = timezone(timedelta(hours=-3))


@pytest.mark.parametrize("field_name", ["title", "author", "summary"])
@pytest.mark.parametrize(
    "blank",
    ["", "   ", "\t\n", "\u00a0", "\u200b", "\ufeff", " \u200b\u00a0 "],
    ids=["vazio", "espacos", "tab-e-quebra", "espaco-nao-quebravel", "largura-zero", "bom", "misturado"],
)
def test_rejects_blank_required_text(field_name: str, blank: str, make_book: Callable[..., Book]) -> None:
    # Texto só com espaço passa por um `if not valor` ingênuo e vira livro sem título no acervo.
    # O espaço não quebrável é o que costuma vir de texto copiado de página web.
    # Bug: o espaço de largura zero (U+200B) e o BOM (U+FEFF) vêm colados de sites, PDFs e planilhas;
    # o `str.strip()` não os remove por não serem "espaço" para o Python, e o livro entrava com
    # título invisível.
    with pytest.raises(InvalidBookError, match=field_name):
        make_book(**{field_name: blank})


@pytest.mark.parametrize("field_name", ["title", "author", "summary"])
def test_strips_surrounding_whitespace_from_text(field_name: str, make_book: Callable[..., Book]) -> None:
    # Sem a limpeza, "Machado de Assis" e "Machado de Assis " seriam autores diferentes na busca.
    book = make_book(**{field_name: "  Machado de Assis \n"})

    assert getattr(book, field_name) == "Machado de Assis"


@pytest.mark.parametrize("field_name", ["title", "author", "summary"])
def test_strips_invisible_characters_from_the_edges(field_name: str, make_book: Callable[..., Book]) -> None:
    # Mesmo bug do caractere invisível, nas pontas: "Machado de Assis" seguido de U+200B parece
    # igual na tela, mas não casaria com "Machado de Assis" na busca.
    book = make_book(**{field_name: "\ufeffMachado de Assis\u200b"})

    assert getattr(book, field_name) == "Machado de Assis"


def test_keeps_invisible_characters_inside_the_text(make_book: Callable[..., Book]) -> None:
    # A limpeza só vale para as pontas: no meio do texto, caracteres de formatação como o U+200D
    # (zero width joiner) compõem emojis e a escrita de idiomas como persa e hindi.
    book = make_book(title="Família \U0001f468\u200d\U0001f469\u200d\U0001f467")

    assert book.title == "Família \U0001f468\u200d\U0001f469\u200d\U0001f467"


def test_accepts_book_not_yet_published(make_book: Callable[..., Book]) -> None:
    # Pré-cadastro: o livro entra no acervo antes do lançamento.
    book = make_book(publication_date=PublicationDate(date(2099, 1, 1)))

    assert book.publication_date.is_published(as_of=date(2026, 10, 27)) is False


def test_created_at_defaults_to_now_in_utc(make_book: Callable[..., Book]) -> None:
    # Caminho de todo cadastro real: ninguém informa `created_at`, ele vem do relógio do domínio.
    before = datetime.now(UTC)
    book = make_book()
    after = datetime.now(UTC)

    assert book.created_at.utcoffset() == timedelta(0)
    assert before <= book.created_at <= after


def test_created_at_in_other_timezone_is_stored_in_utc(make_book: Callable[..., Book]) -> None:
    # Reidratação ou importação com horário de São Paulo: o instante é o mesmo, gravado em UTC.
    book = make_book(created_at=datetime(2026, 10, 27, 22, 0, tzinfo=SAO_PAULO))

    assert book.created_at.utcoffset() == timedelta(0)
    assert (book.created_at.date(), book.created_at.hour) == (date(2026, 10, 28), 1)


def test_rejects_naive_created_at(make_book: Callable[..., Book]) -> None:
    # O erro do relógio chega como erro do livro, para quem cadastra tratar uma exceção só.
    with pytest.raises(InvalidBookError, match="created_at"):
        make_book(created_at=datetime(2026, 10, 27, 22, 0))


def test_each_new_book_gets_its_own_id(make_book: Callable[..., Book]) -> None:
    assert make_book().id != make_book().id


def test_books_with_same_data_but_different_ids_are_different(make_book: Callable[..., Book]) -> None:
    # Duas edições com mesmo título e autor não podem se fundir num set, num dict ou numa
    # deduplicação; identidade é o id.
    first, second = make_book(), make_book()

    assert first != second
    assert len({first, second}) == 2


def test_books_with_same_id_are_the_same_even_if_data_differs(make_book: Callable[..., Book]) -> None:
    # O mesmo livro lido do banco antes e depois de uma correção de título continua sendo o mesmo.
    book_id = uuid4()
    original = make_book(id=book_id, title="Dom Casmuro")
    corrected = make_book(id=book_id, title="Dom Casmurro")

    assert original == corrected
    assert len({original, corrected}) == 1
