"""Testes HTTP dos endpoints de livros, de ponta a ponta: rota, aplicação, domínio e SQLite real.

Cada teste sobe a aplicação com `create_app` e um banco temporário próprio, então nenhum depende
do estado deixado por outro. O `TestClient` usado como context manager executa o lifespan, que
cria o schema, como na subida real.
"""

import json
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


@pytest.mark.parametrize(
    "title",
    ["", "   "],
    ids=["vazio-barrado-pelo-schema", "em-branco-barrado-pelo-dominio"],
)
def test_validation_errors_have_one_shape_and_point_to_the_field(client: TestClient, title: str) -> None:
    # Bug: o schema devolvia uma lista de erros e o domínio devolvia um texto, então o cliente
    # precisava tratar dois formatos conforme o título viesse vazio ou só com espaços.
    response = client.post("/books", json=book_payload(title=title))

    assert response.status_code == 422
    [error] = response.json()["detail"]
    assert error["loc"] == ["body", "title"]
    assert error["msg"]


def test_lone_surrogate_in_the_body_is_rejected_with_422(client: TestClient) -> None:
    # Bug: "\ud800" é um escape JSON válido, mas não é texto UTF-8. O pydantic recusava o campo, e o
    # 422 devolve o valor recebido em `input`; ao gerar a resposta com ele, a API caía com 500.
    body = book_payload(title="abc")
    raw = json.dumps(body).replace('"abc"', '"abc\\ud800"').encode()

    response = client.post("/books", content=raw, headers={"content-type": "application/json"})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "title"]
    assert all_books(client) == []


def test_openapi_documents_only_the_errors_the_api_can_return(client: TestClient) -> None:
    # Bug: o 409 aparecia no contrato sem que nenhuma requisição o produzisse (o `id` é gerado no
    # domínio), e o 422 do cadastro estava sem schema.
    responses = client.get("/openapi.json").json()["paths"]["/books"]["post"]["responses"]

    assert set(responses) == {"201", "422", "429"}
    assert responses["422"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/HTTPValidationError"
    }


# --- Busca ----------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("params", "expected"),
    [({"author": "JOSE"}, ["Iracema"]), ({"title": "casmúrro"}, ["Dom Casmurro"])],
    ids=["por-autor", "por-titulo"],
)
def test_search_by_title_or_author_ignores_case_and_accents(
    client: TestClient, params: dict[str, str], expected: list[str]
) -> None:
    # As duas consultas que o enunciado pede. Livro que não aparece na busca não é encontrado.
    register(client, title="Iracema", author="José de Alencar")
    register(client, title="Dom Casmurro", author="Machado de Assis")

    response = client.get("/books", params=params)

    assert response.status_code == 200
    assert [book["title"] for book in response.json()["items"]] == expected


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
    # Teto de páginas: se o `has_more` nunca virar falso (OFFSET ignorado, por exemplo), o teste
    # falha em vez de pedir páginas para sempre.
    while pages <= expected_pages:
        page = client.get("/books", params={"limit": 2, "offset": offset}).json()
        seen.extend(book["id"] for book in page["items"])
        pages += 1
        if not page["has_more"]:
            break
        offset += page["limit"]

    assert pages == expected_pages
    assert sorted(seen) == sorted(created_ids)


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


def test_search_rejects_unknown_parameters(client: TestClient) -> None:
    # Um filtro com nome errado (`?autor=`, `?q=`) era ignorado e devolvia o acervo inteiro com 200, como
    # se a busca tivesse funcionado. O corpo do cadastro já recusa campo desconhecido; a busca, também.
    response = client.get("/books", params={"autor": "machado"})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "autor"]


def test_validation_error_keeps_accents_as_utf8(client: TestClient) -> None:
    # Bug: a correção do surrogate (bug 10) gravava o 422 inteiro em ASCII, e quem lia a resposta crua
    # (curl, log) via "Parâmetro desconhecido". Só o surrogate precisa de escape.
    response = client.get("/books", params={"autor": "machado"})

    assert "Parâmetro desconhecido".encode() in response.content


def test_search_rejects_offset_beyond_the_ceiling(client: TestClient) -> None:
    # Bug: sem teto, um offset acima do inteiro de 64 bits estourava no sqlite3 e virava 500.
    assert client.get("/books", params={"offset": 10**20}).status_code == 422


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
