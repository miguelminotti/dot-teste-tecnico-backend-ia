"""Entidade Book, o centro do domínio da biblioteca."""

import unicodedata
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
    # Dia do calendário, passado ou futuro (pré-cadastro). Ver a ADR 0003.
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
            raise InvalidBookError(f"created_at: {error}", field="created_at") from error

    # Entidades se comparam pela identidade, não pelos atributos: dois livros com o mesmo título
    # e autor continuam sendo livros diferentes se os ids forem diferentes.
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Book) and other.id == self.id

    def __hash__(self) -> int:
        return hash(self.id)


def _required_text(value: str, field_name: str) -> str:
    """Remove caracteres invisíveis das pontas e recusa texto sem nenhuma letra ou número."""
    cleaned = _strip_invisible(value)
    # "Não vazio" é pouco: acento solto, caractere de controle e os "brancos" de outras escritas
    # (braille em branco, por exemplo) não somem no strip e deixariam o título invisível. Exigir
    # uma letra ou um número cobre todos eles sem listar caso a caso.
    if not any(_is_letter_or_digit(char) for char in cleaned):
        raise InvalidBookError(f"{field_name} precisa ter pelo menos uma letra ou número", field=field_name)
    return cleaned


def _strip_invisible(value: str) -> str:
    """Como `str.strip()`, mas também remove das pontas o que não aparece na tela.

    O `strip()` só conhece espaço em branco. Caracteres de formatação (categoria Unicode "Cf",
    como o espaço de largura zero e o BOM) e de controle ("Cc", como o NUL) não ocupam espaço,
    mas passam por ele.

    No meio do texto eles ficam, porque lá podem ter função (o zero width joiner compõe emojis e
    a escrita de idiomas como persa e hindi). Acentos combinantes também não são removidos das
    pontas: no fim do texto, eles fazem parte da última letra.
    """
    start, end = 0, len(value)
    while start < end and _is_invisible(value[start]):
        start += 1
    while end > start and _is_invisible(value[end - 1]):
        end -= 1
    return value[start:end]


# Letras do alfabeto coreano que não desenham nada (preenchedores). Para o Unicode são letras
# ("Lo"), então precisam ser tratadas à parte.
_HANGUL_FILLERS = frozenset({chr(0x115F), chr(0x1160), chr(0x3164), chr(0xFFA0)})


def _is_invisible(char: str) -> bool:
    return char.isspace() or unicodedata.category(char) in {"Cf", "Cc"} or char in _HANGUL_FILLERS


def _is_letter_or_digit(char: str) -> bool:
    return unicodedata.category(char)[0] in {"L", "N"} and char not in _HANGUL_FILLERS
