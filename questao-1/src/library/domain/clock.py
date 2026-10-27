"""Política de tempo do projeto: todo instante (data + hora) vive em UTC.

Datas puras (`date`, como a de `PublicationDate`) não passam por aqui: um dia do calendário não tem
fuso, e convertê-lo desloca o dia. Ver a seção de datas no README.

Se um cliente trabalhar com outro relógio (America/Sao_Paulo, por exemplo), a conversão acontece
na borda do sistema (entrada e saída da API), nunca no domínio ou no banco.
"""

from datetime import UTC, datetime

from library.domain.errors import NotProvidedTimezoneError


def utc_now() -> datetime:
    """Instante atual em UTC, com fuso explícito.

    Único ponto do projeto que lê o relógio, para que nenhum código chame `datetime.now()`
    sem fuso e acabe gravando o horário local da máquina.
    """
    return datetime.now(UTC)


def to_utc(instant: datetime) -> datetime:
    """Normaliza um instante para UTC.

    Instantes sem fuso (naive) são recusados: não há como saber se "10:00" era em UTC, em São Paulo
    ou no fuso do servidor, e adivinhar é a origem dos erros de horas a mais ou a menos.
    """
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise NotProvidedTimezoneError("instante sem fuso horário; informe o fuso ou use UTC")
    return instant.astimezone(UTC)
