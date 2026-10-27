"""Entidade Book, o centro do domínio da biblioteca."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from library.domain.clock import to_utc, utc_now
from library.domain.errors import InvalidBookError, NotProvidedTimezoneError
from library.domain.publication_date import PublicationDate


@dataclass(slots=True, kw_only=True, eq=False)
class Book:
    """Livro do acervo.

    Toda instância nasce válida: as invariantes são checadas no `__post_init__`, então não existe
    `Book` com título vazio nem com data de cadastro sem fuso circulando pelo sistema.
    """

    title: str
    author: str
    # Dia do calendário, passado ou futuro (pré-cadastro). Ver a seção de datas no README.
    publication_date: PublicationDate
    summary: str
    # Identidade gerada no próprio domínio, sem depender do banco para existir.
    id: UUID = field(default_factory=uuid4)
    # Instante do cadastro, sempre em UTC (sufixo `_at`).
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self.title = _required_text(self.title, "title")
        self.author = _required_text(self.author, "author")
        self.summary = _required_text(self.summary, "summary")

        # Relança como erro do livro para que quem chama trate uma exceção só por entidade.
        try:
            self.created_at = to_utc(self.created_at)
        except NotProvidedTimezoneError as error:
            raise InvalidBookError(f"created_at: {error}") from error

    # Entidades se comparam pela identidade, não pelos atributos: dois livros com o mesmo título
    # e autor continuam sendo livros diferentes se os ids forem diferentes.
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Book) and other.id == self.id

    def __hash__(self) -> int:
        return hash(self.id)


def _required_text(value: str, field_name: str) -> str:
    """Remove espaços das pontas e recusa texto vazio."""
    cleaned = value.strip()
    if not cleaned:
        raise InvalidBookError(f"{field_name} não pode ser vazio")
    return cleaned
