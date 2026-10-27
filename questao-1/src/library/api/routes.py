"""Rotas de livros."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from library.api.dependencies import BookServiceDep, enforce_rate_limit
from library.api.schemas import BookCreate, BookPageResponse, BookResponse, ErrorResponse
from library.application.dtos import RegisterBookCommand

_RATE_LIMITED: dict[int | str, dict[str, Any]] = {
    status.HTTP_429_TOO_MANY_REQUESTS: {"model": ErrorResponse, "description": "Limite de requisições"}
}

# Filtro de busca exige pelo menos um caractere que não seja espaço (`pattern`). Sem isso, "   "
# viraria "contém vazio" e casaria com o acervo inteiro.
_NOT_BLANK = r"\S"

router = APIRouter(prefix="/books", tags=["books"], dependencies=[Depends(enforce_rate_limit)])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra um livro",
    responses={
        status.HTTP_409_CONFLICT: {"model": ErrorResponse, "description": "Livro já cadastrado"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "Dados inválidos (campo vazio, data fora do formato)"},
        **_RATE_LIMITED,
    },
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


@router.get("", summary="Busca livros por título ou autor", responses=_RATE_LIMITED)
def search_books(
    service: BookServiceDep,
    title: Annotated[str | None, Query(max_length=300, pattern=_NOT_BLANK, description="Trecho do título.")] = None,
    author: Annotated[
        str | None, Query(max_length=200, pattern=_NOT_BLANK, description="Trecho do nome do autor.")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Tamanho da página.")] = 20,
    offset: Annotated[int, Query(ge=0, description="Quantos resultados pular.")] = 0,
) -> BookPageResponse:
    """Busca por trecho do título e/ou do autor, sem diferenciar maiúsculas nem acentos.

    "jose" encontra "José de Alencar". Com os dois filtros, o livro precisa casar com ambos; sem
    filtro, lista o acervo. O resultado vem em ordem alfabética de título, paginado: use
    `has_more` para saber se há próxima página e `offset` para pedi-la.
    """
    page = service.search(title=title, author=author, limit=limit, offset=offset)
    return BookPageResponse.model_validate(page)
