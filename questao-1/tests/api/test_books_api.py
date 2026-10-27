"""Testes HTTP dos endpoints de livros, de ponta a ponta: rota, aplicação, domínio e SQLite real.

Cada teste sobe a aplicação com `create_app` e um banco temporário próprio, então nenhum depende
do estado deixado por outro. O `TestClient` usado como context manager executa o lifespan, que
cria o schema, como na subida real.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from library.api.app import create_app
from library.api.settings import Settings

# Limite alto o bastante para nunca interferir nos testes que não são de rate limiting.
NO_RATE_LIMIT = 10_000
MISSING = object()


@contextmanager
def running_api(database: Path, *, rate_limit_requests: int = NO_RATE_LIMIT) -> Iterator[TestClient]:
    settings = Settings(database_path=database, rate_limit_requests=rate_limit_requests)
    with TestClient(create_app(settings)) as client:
        yield client


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    with running_api(tmp_path / "api.db") as api:
        yield api


def book_payload(**overrides: Any) -> dict[str, Any]:
    """Corpo válido de cadastro; `MISSING` remove o campo."""
    payload: dict[str, Any] = {
        "title": "Dom Casmurro",
        "author": "Machado de Assis",
        "publication_date": "1899-01-01",
        "summary": "Bentinho narra o ciúme que sente de Capitu.",
    }
    payload.update(overrides)
    return {key: value for key, value in payload.items() if value is not MISSING}


def register(client: TestClient, **overrides: Any) -> dict[str, Any]:
    response = client.post("/books", json=book_payload(**overrides))
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def all_books(client: TestClient) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = client.get("/books", params={"limit": 100}).json()["items"]
    return items


# --- Cadastro ---------------------------------------------------------------------------------------


def test_register_returns_the_created_book_and_persists_it(client: TestClient) -> None:
    # O cliente guarda o `id` devolvido; se ele não for o mesmo que ficou no banco, ou se o livro
    # não tiver sido gravado, o cadastro "deu certo" e o livro não existe.
    created = register(client)

    assert set(created) == {"id", "title", "author", "summary", "publication_date", "is_published", "created_at"}
    assert UUID(created["id"])
    assert datetime.fromisoformat(created["created_at"]).utcoffset() == timedelta(0)
    assert [book["id"] for book in all_books(client)] == [created["id"]]


@pytest.mark.parametrize(
    ("publication_date", "is_published"),
    [("1899-01-01", True), ("2099-01-01", False)],
    ids=["ja-publicado", "pre-cadastro"],
)
def test_is_published_follows_the_publication_date(
    client: TestClient, publication_date: str, is_published: bool
) -> None:
    # Pré-cadastro aparecendo como publicado é livro anunciado como disponível sem existir.
    created = register(client, publication_date=publication_date)

    assert created["is_published"] is is_published
    assert all_books(client)[0]["is_published"] is is_published


@pytest.mark.parametrize(
    "overrides",
    [
        # Sem a validação estrita, o pydantic transformaria 0 em 01/01/1970 em silêncio.
        {"publication_date": 0},
        {"publication_date": "2026-10-28T00:00:00"},
        {"publication_date": "28/10/2026"},
        {"publication_date": "2026-02-30"},
        # O cliente não pode escolher o próprio `id` nem dizer que o livro está publicado.
        {"id": "00000000-0000-4000-8000-000000000000"},
        {"is_published": True},
        {"summary": MISSING},
        {"summary": None},
        {"title": "a" * 301},
        # Estes passam pelo schema e são barrados pelo domínio.
        {"title": "   "},
        {"author": "\N{ZERO WIDTH SPACE}"},
    ],
    ids=[
        "data-numerica",
        "data-com-hora",
        "data-dd-mm-aaaa",
        "dia-inexistente",
        "id-do-cliente",
        "is-published-do-cliente",
        "sem-resumo",
        "resumo-nulo",
        "titulo-acima-do-limite",
        "titulo-em-branco",
        "autor-invisivel",
    ],
)
def test_invalid_payload_is_rejected_and_nothing_is_saved(client: TestClient, overrides: dict[str, Any]) -> None:
    response = client.post("/books", json=book_payload(**overrides))

    assert response.status_code == 422
    assert all_books(client) == []


def test_domain_rejection_says_which_field_is_wrong(client: TestClient) -> None:
    # Erro de domínio sai como 422 com mensagem útil, não como 500.
    response = client.post("/books", json=book_payload(title="   "))

    assert response.status_code == 422
    assert "title" in response.json()["detail"]


# --- Busca ----------------------------------------------------------------------------------------


def test_search_by_author_ignores_case_and_accents(client: TestClient) -> None:
    register(client, title="Iracema", author="José de Alencar")
    register(client, title="Dom Casmurro", author="Machado de Assis")

    response = client.get("/books", params={"author": "JOSE"})

    assert response.status_code == 200
    assert [book["title"] for book in response.json()["items"]] == ["Iracema"]


@pytest.mark.parametrize(
    ("total", "expected_pages"),
    [(5, 3), (4, 2)],
    ids=["ultima-pagina-incompleta", "total-multiplo-do-limit"],
)
def test_paging_through_the_results_returns_every_book_exactly_once(
    client: TestClient, total: int, expected_pages: int
) -> None:
    # Um erro de uma unidade no `offset` ou no `has_more` repete ou esconde livros entre páginas.
    # O total múltiplo do `limit` é o caso traiçoeiro: a última página vem cheia, e um `has_more`
    # errado mandaria o cliente pedir uma página vazia.
    created_ids = {register(client, title=f"Livro {number}")["id"] for number in range(total)}

    seen: list[str] = []
    offset, pages = 0, 0
    while True:
        page = client.get("/books", params={"limit": 2, "offset": offset}).json()
        seen.extend(book["id"] for book in page["items"])
        pages += 1
        if not page["has_more"]:
            break
        offset += page["limit"]

    assert sorted(seen) == sorted(created_ids)
    assert pages == expected_pages


def test_search_without_limit_returns_the_default_page(client: TestClient) -> None:
    # Sem o limite padrão, um GET sem parâmetros devolveria o acervo inteiro.
    for number in range(21):
        register(client, title=f"Livro {number:02d}")

    page = client.get("/books").json()

    assert (len(page["items"]), page["limit"], page["has_more"]) == (20, 20, True)


@pytest.mark.parametrize(
    "params",
    [{"limit": 0}, {"limit": 101}, {"limit": -1}, {"offset": -1}, {"title": "   "}, {"author": ""}],
    ids=["limit-zero", "limit-acima-do-maximo", "limit-negativo", "offset-negativo", "titulo-em-branco", "autor-vazio"],
)
def test_search_rejects_parameters_that_would_bypass_pagination(client: TestClient, params: dict[str, Any]) -> None:
    # `LIMIT -1` no SQLite é "sem limite", e um filtro em branco vira "contém vazio": os dois
    # devolveriam o acervo inteiro.
    assert client.get("/books", params=params).status_code == 422


# --- Rate limiting --------------------------------------------------------------------------------


def test_client_over_the_limit_gets_429_with_retry_after(tmp_path: Path) -> None:
    with running_api(tmp_path / "api.db", rate_limit_requests=2) as api:
        statuses = [api.get("/books").status_code for _ in range(3)]
        blocked = api.get("/books")

    assert statuses == [200, 200, 429]
    assert blocked.status_code == 429
    assert 0 < int(blocked.headers["Retry-After"]) <= 60


def test_forged_forwarded_header_does_not_bypass_the_limit(tmp_path: Path) -> None:
    # Se o limite confiasse no `X-Forwarded-For`, bastaria inventar um IP por requisição.
    with running_api(tmp_path / "api.db", rate_limit_requests=1) as api:
        api.get("/books")
        response = api.get("/books", headers={"X-Forwarded-For": "203.0.113.7"})

    assert response.status_code == 429
