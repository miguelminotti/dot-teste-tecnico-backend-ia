"""Fixtures compartilhadas entre as suítes de teste."""

from collections.abc import Callable
from datetime import date
from typing import Any

import pytest

from library.domain.book import Book
from library.domain.publication_date import PublicationDate


def _make_book(**overrides: Any) -> Book:
    fields: dict[str, Any] = {
        "title": "Dom Casmurro",
        "author": "Machado de Assis",
        "publication_date": PublicationDate(date(1899, 1, 1)),
        "summary": "Bentinho narra o ciúme que sente de Capitu.",
    }
    fields.update(overrides)
    return Book(**fields)


@pytest.fixture
def make_book() -> Callable[..., Book]:
    """Fábrica de livro válido; cada teste sobrescreve só o campo que está exercitando.

    Saiu do `test_book.py` quando a suíte da infraestrutura passou a precisar dela também.
    """
    return _make_book
