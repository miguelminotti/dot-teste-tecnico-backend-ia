"""Infraestrutura: implementações concretas das portas do domínio (hoje, o SQLite)."""

from library.infrastructure.database import connect, create_schema
from library.infrastructure.sqlite_book_repository import SqliteBookRepository

__all__ = ["SqliteBookRepository", "connect", "create_schema"]
