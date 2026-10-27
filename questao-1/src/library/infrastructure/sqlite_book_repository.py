"""Repositório de livros sobre SQLite."""

import sqlite3
import unicodedata
from datetime import date, datetime
from uuid import UUID

from library.domain.book import Book
from library.domain.errors import BookAlreadyExistsError
from library.domain.publication_date import PublicationDate

# As queries montam SQL com f-string só a partir destas constantes do módulo. Valor vindo de fora
# (título, autor, trecho buscado) sempre vai como parâmetro nomeado, nunca concatenado no SQL.
_COLUMNS = "id, title, author, summary, publication_date, created_at"

# Caractere de escape do LIKE, para que "%" e "_" digitados na busca sejam texto.
_LIKE_ESCAPE = "\\"


class SqliteBookRepository:
    """Implementa `BookRepository` com o `sqlite3` da biblioteca padrão.

    Recebe a conexão pronta: quem cria e fecha a conexão (a API, por requisição) é quem controla o
    ciclo de vida dela.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, book: Book) -> None:
        try:
            # `with connection` abre a transação e faz commit no fim, ou rollback se der erro.
            with self._connection:
                self._connection.execute(
                    f"""
                    INSERT INTO books ({_COLUMNS}, title_search, author_search)
                    VALUES (:id, :title, :author, :summary, :publication_date, :created_at,
                            :title_search, :author_search)
                    """,
                    {
                        "id": str(book.id),
                        "title": book.title,
                        "author": book.author,
                        "summary": book.summary,
                        "publication_date": book.publication_date.value.isoformat(),
                        # Microssegundos sempre presentes: sem eles, o `isoformat` omite a fração
                        # quando ela é zero, e o texto deixa de ordenar na mesma ordem do tempo.
                        "created_at": book.created_at.isoformat(timespec="microseconds"),
                        "title_search": normalize_for_search(book.title),
                        "author_search": normalize_for_search(book.author),
                    },
                )
        except sqlite3.IntegrityError as error:
            # Só a chave primária duplicada vira erro de domínio. Um CHECK violado é bug do
            # repositório (o domínio já garante os formatos) e deve estourar como está.
            if error.sqlite_errorname == "SQLITE_CONSTRAINT_PRIMARYKEY":
                raise BookAlreadyExistsError(f"livro {book.id} já cadastrado") from error
            raise

    def search(self, *, title: str | None = None, author: str | None = None) -> list[Book]:
        conditions: list[str] = []
        params: dict[str, str] = {}
        if title is not None:
            conditions.append(f"title_search LIKE :title ESCAPE '{_LIKE_ESCAPE}'")
            params["title"] = _contains_pattern(title)
        if author is not None:
            conditions.append(f"author_search LIKE :author ESCAPE '{_LIKE_ESCAPE}'")
            params["author"] = _contains_pattern(author)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        # Ordem alfabética e estável: o `id` desempata livros com mesmo título e autor.
        rows = self._connection.execute(
            f"SELECT {_COLUMNS} FROM books {where} ORDER BY title_search, author_search, id",
            params,
        ).fetchall()
        return [_to_book(row) for row in rows]


def normalize_for_search(text: str) -> str:
    """Forma do texto usada na busca: sem diferença de maiúsculas nem de acentos.

    O LIKE do SQLite só ignora maiúsculas em ASCII ("érico" não acha "Érico") e nunca ignora
    acentos ("jose" não acha "José"). Gravar e buscar pela forma normalizada resolve os dois.

    - `casefold` é a versão agressiva do `lower` para comparação ("ß" vira "ss").
    - NFKD separa a letra do acento ("é" vira "e" + acento) e desfaz ligaduras ("ﬁ" vira "fi").
    - Os acentos soltos (caracteres "combining") são descartados.
    """
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _contains_pattern(text: str) -> str:
    """Padrão LIKE de "contém o trecho", com os curingas do usuário escapados."""
    escaped = (
        normalize_for_search(text.strip())
        .replace(_LIKE_ESCAPE, _LIKE_ESCAPE * 2)
        .replace("%", _LIKE_ESCAPE + "%")
        .replace("_", _LIKE_ESCAPE + "_")
    )
    return f"%{escaped}%"


def _to_book(row: sqlite3.Row) -> Book:
    """Reidrata a entidade a partir da linha; as invariantes do `Book` rodam de novo aqui."""
    return Book(
        id=UUID(row["id"]),
        title=row["title"],
        author=row["author"],
        summary=row["summary"],
        publication_date=PublicationDate(date.fromisoformat(row["publication_date"])),
        created_at=datetime.fromisoformat(row["created_at"]),
    )
