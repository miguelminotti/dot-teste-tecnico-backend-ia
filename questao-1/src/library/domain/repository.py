"""Porta de persistência do livro.

O domínio diz o que precisa (guardar e buscar livros) e a infraestrutura diz como. A camada de
aplicação depende só deste contrato, então trocar o SQLite por outro banco não toca nas regras.
"""

from typing import Protocol

from library.domain.book import Book


class BookRepository(Protocol):
    """Contrato de persistência do acervo.

    Leitura e escrita ficam no mesmo repositório: com uma escrita (cadastro) e uma leitura (busca),
    separar comandos de consultas (CQRS) seria estrutura sem ganho.
    """

    def add(self, book: Book) -> None:
        """Guarda um livro novo. Levanta `BookAlreadyExistsError` se o `id` já existir."""
        ...

    def search(self, *, title: str | None = None, author: str | None = None, limit: int, offset: int = 0) -> list[Book]:
        """Busca livros por trecho do título e/ou do autor, sem diferenciar maiúsculas nem acentos.

        Com os dois filtros, o livro precisa casar com ambos; sem filtro, considera o acervo inteiro.
        `limit` é obrigatório para que nenhuma chamada devolva o acervo inteiro de uma vez: quem
        chama decide o tamanho da página. Levanta `ValueError` para `limit < 1` ou `offset < 0`.
        """
        ...
