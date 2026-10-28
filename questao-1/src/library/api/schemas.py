"""Contrato HTTP: o que a API recebe e devolve.

Os limites de tamanho dos textos moram aqui, não na entidade: não são regra de negócio, são
proteção da borda contra payload abusivo (ADR 0002). Vazio e espaços continuam com o domínio.
"""

import re
from datetime import date, datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _require_iso_date_text(value: Any) -> Any:
    """Aceita a data só como texto `AAAA-MM-DD`.

    No modo padrão o pydantic aceita `0` (vira 01/01/1970) e `"2026-10-28T00:00:00"` como data.
    Um número enviado por engano viraria um livro de 1970 em silêncio, e data com hora contraria
    a data de publicação como dia puro (ADR 0003).
    """
    if not isinstance(value, str) or not _ISO_DATE.fullmatch(value):
        raise ValueError("use o formato AAAA-MM-DD")
    return value


PublicationDateField = Annotated[
    date,
    BeforeValidator(_require_iso_date_text),
    Field(description="Dia da publicação, passado ou futuro (pré-cadastro), no formato AAAA-MM-DD."),
]


class BookCreate(BaseModel):
    """Corpo do cadastro de livro."""

    # `forbid`: campo desconhecido é erro, e não ignorado. O cliente não consegue mandar `id`,
    # `created_at` ou `is_published` achando que foram aceitos.
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "title": "Dom Casmurro",
                    "author": "Machado de Assis",
                    "publication_date": "1899-01-01",
                    "summary": "Bentinho narra o ciúme que sente de Capitu.",
                }
            ]
        },
    )

    title: Annotated[str, Field(min_length=1, max_length=300, description="Título do livro.")]
    author: Annotated[str, Field(min_length=1, max_length=200, description="Autor ou autores.")]
    publication_date: PublicationDateField
    summary: Annotated[str, Field(min_length=1, max_length=5000, description="Resumo do livro.")]


class BookResponse(BaseModel):
    """Livro como a API o devolve."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    author: str
    summary: str
    publication_date: date = Field(description="Dia da publicação (AAAA-MM-DD).")
    is_published: bool = Field(
        description="Se o livro já foi publicado, no dia atual do fuso da biblioteca. Falso para pré-cadastros."
    )
    created_at: datetime = Field(description="Instante do cadastro, em UTC.")


class BookPageResponse(BaseModel):
    """Uma página do resultado da busca."""

    model_config = ConfigDict(from_attributes=True)

    items: list[BookResponse]
    limit: int = Field(description="Tamanho máximo da página pedida.")
    offset: int = Field(description="Quantos resultados foram pulados.")
    has_more: bool = Field(description="Se existe próxima página; para pedi-la, use `offset` igual a `offset + limit`.")


class ErrorResponse(BaseModel):
    """Erro devolvido pela API."""

    detail: str
