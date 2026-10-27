"""Dependências das rotas: configuração, conexão por requisição, serviço e rate limiting.

É aqui que as camadas se montam: a API pede um `BookService` e recebe um com o repositório SQLite
por trás. As rotas não sabem que existe banco.
"""

import math
import sqlite3
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from library.api.rate_limit import FixedWindowRateLimiter
from library.api.settings import Settings
from library.application.book_service import BookService, today_in
from library.infrastructure.database import connect
from library.infrastructure.sqlite_book_repository import SqliteBookRepository


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_connection(settings: Annotated[Settings, Depends(get_settings)]) -> Iterator[sqlite3.Connection]:
    """Uma conexão por requisição, fechada ao fim dela mesmo se a rota falhar."""
    connection = connect(settings.database_path, check_same_thread=False)
    try:
        yield connection
    finally:
        connection.close()


def get_book_service(
    connection: Annotated[sqlite3.Connection, Depends(get_connection)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> BookService:
    return BookService(SqliteBookRepository(connection), today=today_in(settings.timezone))


BookServiceDep = Annotated[BookService, Depends(get_book_service)]


def enforce_rate_limit(request: Request) -> None:
    """Recusa com 429 o cliente que passou do limite, dizendo em `Retry-After` quando tentar de novo.

    O cliente é identificado pelo IP da conexão. O cabeçalho `X-Forwarded-For` é ignorado de
    propósito: sem um proxy confiável na frente, qualquer cliente o forjaria com um IP diferente a
    cada requisição e nunca seria limitado. Atrás de um proxy, o servidor (uvicorn
    `--forwarded-allow-ips`) é que deve reescrever o IP do cliente.
    """
    limiter: FixedWindowRateLimiter = request.app.state.rate_limiter
    client = request.client.host if request.client else "desconhecido"
    retry_after = limiter.acquire(client)
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="limite de requisições atingido; tente de novo em instantes",
            headers={"Retry-After": str(math.ceil(retry_after))},
        )
