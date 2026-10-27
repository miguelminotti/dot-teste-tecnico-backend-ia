"""Conexão e schema do SQLite.

Usa o `sqlite3` da biblioteca padrão, sem ORM: uma tabela só, SQL explícito e controle total de
como datas são gravadas. Datas nunca são passadas ao `sqlite3` como `date`/`datetime`; o adaptador
padrão dele está deprecado desde o Python 3.12 e grava instantes sem fuso. O repositório converte
para texto ISO 8601 antes de gravar.
"""

import sqlite3
from pathlib import Path

# STRICT faz o SQLite recusar valor de tipo errado em vez de convertê-lo em silêncio.
# Os CHECKs repetem no banco a política de datas (ADR 0002), para valer também para quem gravar
# sem passar pelo repositório.
SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id               TEXT PRIMARY KEY,
    title            TEXT NOT NULL,
    author           TEXT NOT NULL,
    summary          TEXT NOT NULL,
    -- Dia do calendário (AAAA-MM-DD), sem hora nem fuso. date() devolve NULL ou outro dia
    -- para valor inválido (2026-02-30 vira 2026-03-02), e o CHECK recusa os dois casos.
    publication_date TEXT NOT NULL CHECK (date(publication_date) IS publication_date),
    -- Instante em UTC, ISO 8601 com o offset explícito.
    created_at       TEXT NOT NULL CHECK (created_at LIKE '%+00:00'),
    -- Título e autor normalizados (sem maiúsculas e sem acentos), usados só na busca.
    title_search     TEXT NOT NULL,
    author_search    TEXT NOT NULL
) STRICT;
"""


def connect(database: str | Path) -> sqlite3.Connection:
    """Abre uma conexão com linhas acessíveis por nome de coluna."""
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    return connection


def create_schema(connection: sqlite3.Connection) -> None:
    """Cria a tabela se ela ainda não existir.

    `CREATE TABLE IF NOT EXISTS` no lugar de migrations: com uma tabela e nenhum dado em produção,
    uma ferramenta de migração seria estrutura sem uso. Ela entra na primeira mudança de schema.
    """
    connection.executescript(SCHEMA)
