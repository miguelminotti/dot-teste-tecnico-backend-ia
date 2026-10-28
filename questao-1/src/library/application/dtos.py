"""Objetos que entram e saem da camada de aplicação.

Quem está fora do domínio (a API, hoje) nunca recebe a entidade `Book`: recebe um DTO com tipos
simples. Assim a entidade pode mudar (ganhar comportamento, trocar um campo por value object) sem
mudar o contrato de quem a consome, e nada fora do domínio consegue chamar comportamento dela.
"""

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class RegisterBookCommand:
    """Dados para cadastrar um livro, como chegam de quem pede o cadastro."""

    title: str
    author: str
    publication_date: date
    summary: str


@dataclass(frozen=True, slots=True, kw_only=True)
class BookDTO:
    """Livro como é exposto para fora da aplicação."""

    id: UUID
    title: str
    author: str
    summary: str
    publication_date: date
    # Derivado da data de publicação no dia da biblioteca (ADR 0003); nunca é guardado.
    is_published: bool
    created_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class BookPage:
    """Uma página da busca.

    `has_more` diz se existe próxima página sem precisar contar o resultado inteiro: a aplicação
    pede uma linha a mais do que o limite e só olha se ela veio.
    """

    items: list[BookDTO]
    limit: int
    offset: int
    has_more: bool
