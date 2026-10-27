"""Ponto de entrada: `uv run library` ou `uv run uvicorn library.api.main:app`."""

import uvicorn

from library.api.app import create_app

app = create_app()


def run() -> None:
    uvicorn.run("library.api.main:app", host="127.0.0.1", port=8000)
