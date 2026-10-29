"""Montagem da aplicação FastAPI."""

import json
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, closing

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response

from library.api.rate_limit import FixedWindowRateLimiter
from library.api.routes import router
from library.api.settings import Settings
from library.domain.errors import BookAlreadyExistsError, DomainError
from library.infrastructure.database import connect, create_schema

# Metade de um par UTF-16 sem a outra: vale como escape JSON ("\ud800"), mas não existe em UTF-8.
_LONE_SURROGATE = re.compile("[\ud800-\udfff]")

_DESCRIPTION = """
Cadastro e consulta de livros de uma biblioteca virtual.

- **Sem autenticação**: o enunciado não pede; use em ambiente controlado.
- **Rate limiting** por IP: acima do limite, a resposta é `429` com o cabeçalho `Retry-After`.
- **Datas**: `publication_date` é um dia (`AAAA-MM-DD`); `created_at` é um instante em UTC.
"""


def create_app(settings: Settings | None = None) -> FastAPI:
    """Cria a aplicação; os testes passam a própria configuração (banco temporário, limite baixo)."""
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        # O schema é garantido a cada subida; `CREATE TABLE IF NOT EXISTS` não apaga o acervo.
        with closing(connect(settings.database_path)) as connection:
            create_schema(connection)
        yield

    app = FastAPI(title="Biblioteca virtual", version="0.1.0", description=_DESCRIPTION, lifespan=lifespan)
    app.state.settings = settings
    app.state.rate_limiter = FixedWindowRateLimiter(
        max_requests=settings.rate_limit_requests, window_seconds=settings.rate_limit_window_seconds
    )
    app.include_router(router)
    app.add_exception_handler(RequestValidationError, _request_validation_error)
    app.add_exception_handler(BookAlreadyExistsError, _book_already_exists)
    app.add_exception_handler(DomainError, _domain_error)
    return app


# Erros de domínio viram respostas HTTP aqui, num lugar só, para as rotas não precisarem de
# try/except. O Starlette escolhe o handler da classe mais específica, então o 409 vence o 422.


def _request_validation_error(_: Request, error: Exception) -> Response:
    # O mesmo 422 do FastAPI, com um cuidado a mais. O FastAPI devolve o valor recebido em `input`, e com
    # um surrogate solto a resposta padrão caía com 500 ao virar UTF-8. Só o surrogate volta escapado,
    # como veio no JSON; os acentos ficam em UTF-8, legíveis para quem lê a resposta crua.
    errors = error.errors() if isinstance(error, RequestValidationError) else []
    body = json.dumps({"detail": jsonable_encoder(errors)}, ensure_ascii=False)
    body = _LONE_SURROGATE.sub(lambda match: f"\\u{ord(match.group()):04x}", body)
    return Response(content=body, status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, media_type="application/json")


def _book_already_exists(_: Request, error: Exception) -> JSONResponse:
    # Defesa, fora do contrato: o `id` é gerado no domínio, então nenhuma requisição produz um
    # livro duplicado. Se acontecer (colisão de UUID), a resposta é 409, não 500.
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(error)})


def _domain_error(_: Request, error: Exception) -> JSONResponse:
    # Mesmo formato do 422 do pydantic (`HTTPValidationError`): o cliente trata um formato só, venha
    # o erro do schema ("" num campo) ou do domínio ("   " no mesmo campo).
    field = error.field if isinstance(error, DomainError) else None
    loc = ["body", field] if field else ["body"]
    detail = [{"type": "domain_error", "loc": loc, "msg": str(error)}]
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content={"detail": detail})
