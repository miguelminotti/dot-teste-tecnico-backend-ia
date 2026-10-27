"""Erros do domínio.

Ficam separados das exceções do Python para que as camadas de fora (API, por exemplo)
consigam distinguir "regra de negócio violada" de "bug no código" e responder de acordo.
"""


class DomainError(Exception):
    """Base de todo erro que o domínio levanta de propósito."""


class InvalidBookError(DomainError):
    """Um dado de entrada viola uma invariante do livro.

    Não se chama `ValidationError` para não se confundir com a classe homônima do pydantic,
    que vai conviver com esta na camada da API.
    """


# Not provided UTC error
class NotProvidedTimezoneError(DomainError):
    """Erro levantado quando um valor de data/hora com fuso horário obrigatório não é fornecido."""


class InvalidPublicationDateError(DomainError):
    """A data de publicação não é um dia do calendário válido (por exemplo, veio com hora)."""
