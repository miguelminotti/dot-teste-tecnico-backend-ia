"""Casos de uso do acervo: cadastrar e buscar livros."""

from collections.abc import Callable
from datetime import date, tzinfo

from library.application.dtos import BookDTO, BookPage, RegisterBookCommand
from library.domain.book import Book
from library.domain.clock import utc_now
from library.domain.publication_date import PublicationDate
from library.domain.repository import BookRepository


def today_in(timezone: tzinfo) -> Callable[[], date]:
    """Fábrica do "hoje" da biblioteca: o dia do calendário no fuso em que ela opera.

    O instante vem do relógio do domínio (UTC) e só aqui vira dia, no fuso escolhido. Às 22h de
    27/10 em São Paulo o dia em UTC já é 28/10; com o fuso da biblioteca, ainda é 27/10, e um
    lançamento de 28/10 não aparece como publicado antes da hora (ADR 0003).
    """

    def today() -> date:
        return utc_now().astimezone(timezone).date()

    return today


class BookService:
    """Orquestra domínio e repositório; a API fala só com esta classe.

    Recebe o repositório pela porta do domínio (`BookRepository`), não pela implementação SQLite,
    e o "hoje" como função, para que os testes fixem o dia sem mexer no relógio.
    """

    def __init__(self, repository: BookRepository, today: Callable[[], date]) -> None:
        self._repository = repository
        self._today = today

    def register(self, command: RegisterBookCommand) -> BookDTO:
        """Cadastra um livro. As invariantes são do `Book`; erros chegam como `DomainError`."""
        book = Book(
            title=command.title,
            author=command.author,
            publication_date=PublicationDate(command.publication_date),
            summary=command.summary,
        )
        self._repository.add(book)
        return self._to_dto(book, self._today())

    def search(self, *, title: str | None = None, author: str | None = None, limit: int, offset: int = 0) -> BookPage:
        """Busca uma página de livros por trecho do título e/ou do autor."""
        # Uma linha a mais que o limite responde "tem próxima página?" sem um COUNT, que no
        # LIKE '%trecho%' percorreria a tabela outra vez.
        found = self._repository.search(title=title, author=author, limit=limit + 1, offset=offset)
        # Um "hoje" por página: todos os livros da resposta usam o mesmo dia, mesmo que a
        # meia-noite passe no meio da montagem.
        today = self._today()
        return BookPage(
            items=[self._to_dto(book, today) for book in found[:limit]],
            limit=limit,
            offset=offset,
            has_more=len(found) > limit,
        )

    @staticmethod
    def _to_dto(book: Book, today: date) -> BookDTO:
        return BookDTO(
            id=book.id,
            title=book.title,
            author=book.author,
            summary=book.summary,
            publication_date=book.publication_date.value,
            is_published=book.publication_date.is_published(as_of=today),
            created_at=book.created_at,
        )
