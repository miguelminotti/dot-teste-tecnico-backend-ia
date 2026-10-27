"""Value object da data de publicação de um livro."""

from dataclasses import dataclass
from datetime import date, datetime

from library.domain.errors import InvalidPublicationDateError


@dataclass(frozen=True, slots=True)
class PublicationDate:
    """Dia em que o livro foi ou será publicado.

    Pode estar no passado ou no futuro: livros podem ser pré-cadastrados antes do lançamento.
    Se o livro já está publicado não é guardado em lugar nenhum, é derivado desta data com
    `is_published`, para nunca haver uma flag discordando da data.

    Imutável e comparado por valor: duas instâncias com o mesmo dia são a mesma data.
    """

    value: date

    def __post_init__(self) -> None:
        # `datetime` é subclasse de `date`, então o mypy aceita um datetime aqui sem reclamar.
        # Barramos em tempo de execução para a data de publicação nunca carregar hora ou fuso.
        if isinstance(self.value, datetime):
            raise InvalidPublicationDateError("a data de publicação deve ser um dia, sem hora")

    def is_published(self, as_of: date) -> bool:
        """Diz se o livro já está publicado no dia `as_of` (o próprio dia de lançamento conta).

        O dia de referência é obrigatório e vem de quem chama, em vez de ser lido do relógio aqui.
        Qual "hoje" vale é decisão de negócio: às 22h de 27/10 em São Paulo, o dia em UTC já é 28/10,
        e um lançamento de 28/10 apareceria publicado três horas antes. Quem conhece o fuso que
        importa (a camada de aplicação) decide; o value object só compara datas.
        """
        return self.value <= as_of
