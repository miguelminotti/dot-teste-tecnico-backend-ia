"""Rotas de livros."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.exceptions import RequestValidationError

from library.api.dependencies import BookServiceDep, enforce_rate_limit
from library.api.schemas import BookCreate, BookPageResponse, BookResponse, ErrorResponse
from library.application.dtos import RegisterBookCommand

_RATE_LIMITED: dict[int | str, dict[str, Any]] = {
    status.HTTP_429_TOO_MANY_REQUESTS: {"model": ErrorResponse, "description": "Limite de requisições"}
}

# Filtro de busca exige pelo menos um caractere que não seja espaço (`pattern`). Sem isso, "   "
# viraria "contém vazio" e casaria com o acervo inteiro.
_NOT_BLANK = r"\S"

# Teto do offset: sem ele, um valor acima do inteiro de 64 bits estoura no sqlite3 e vira 500. Um
# milhão de livros pulados já é mais do que paginação por offset atende bem; além disso, o caminho
# seria paginação por cursor.
_MAX_OFFSET = 1_000_000

router = APIRouter(prefix="/books", tags=["books"], dependencies=[Depends(enforce_rate_limit)])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra um livro",
    # O 422 não é declarado aqui de propósito: o FastAPI o documenta com o schema
    # `HTTPValidationError`, que é o mesmo formato devolvido pelos erros de domínio.
    responses=_RATE_LIMITED,
)
def register_book(payload: BookCreate, service: BookServiceDep) -> BookResponse:
    """Cadastra um livro no acervo e devolve o livro com `id` e `created_at` gerados.

    A data de publicação pode estar no futuro: livros podem ser pré-cadastrados antes do
    lançamento, e voltam com `is_published` falso até o dia chegar.
    """
    book = service.register(
        RegisterBookCommand(
            title=payload.title,
            author=payload.author,
            publication_date=payload.publication_date,
            summary=payload.summary,
        )
    )
    return BookResponse.model_validate(book)


_SEARCH_PARAMETERS = {"title", "author", "limit", "offset"}


def _reject_unknown_query_parameters(request: Request) -> None:
    """Recusa parâmetro que a busca não conhece, como o corpo do cadastro recusa campo desconhecido.

    Ignorado, um filtro com nome errado (`?autor=`) devolveria o acervo inteiro com 200, como se a busca
    tivesse funcionado. O erro sai no mesmo formato do 422 de validação.
    """
    unknown = sorted(set(request.query_params) - _SEARCH_PARAMETERS)
    if unknown:
        raise RequestValidationError(
            [{"type": "extra_forbidden", "loc": ["query", name], "msg": "Parâmetro desconhecido"} for name in unknown]
        )


@router.get(
    "",
    summary="Busca livros por título ou autor",
    responses=_RATE_LIMITED,
    dependencies=[Depends(_reject_unknown_query_parameters)],
)
def search_books(
    service: BookServiceDep,
    title: Annotated[str | None, Query(max_length=300, pattern=_NOT_BLANK, description="Trecho do título.")] = None,
    author: Annotated[
        str | None, Query(max_length=200, pattern=_NOT_BLANK, description="Trecho do nome do autor.")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Tamanho da página.")] = 20,
    offset: Annotated[int, Query(ge=0, le=_MAX_OFFSET, description="Quantos resultados pular.")] = 0,
) -> BookPageResponse:
    """Busca por trecho do título e/ou do autor, sem diferenciar maiúsculas nem acentos.

    "jose" encontra "José de Alencar". Com os dois filtros, o livro precisa casar com ambos; sem
    filtro, lista o acervo. O resultado vem em ordem alfabética de título, paginado: use
    `has_more` para saber se há próxima página e `offset` para pedi-la.
    """
    page = service.search(title=title, author=author, limit=limit, offset=offset)
    return BookPageResponse.model_validate(page)
