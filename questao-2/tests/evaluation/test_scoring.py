import pytest

from chatbot.evaluation.judge import CRITERIA, Criterion, KeyPointCheck, TurnVerdict
from chatbot.evaluation.run import score_verdicts


def _verdict(covered: list[bool], *, factual_accuracy: bool = True) -> TurnVerdict:
    """Veredito com a cobertura pedida e todos os critérios aprovados, exceto o que o teste mudar."""
    criteria = {name: Criterion(reasoning="ok", passed=True) for name in CRITERIA}
    criteria["factual_accuracy"] = Criterion(reasoning="afirmação errada", passed=factual_accuracy)
    return TurnVerdict(
        key_points=[KeyPointCheck(reasoning="motivo", covered=value) for value in covered],
        **criteria,
    )


def _scores(verdicts: list[TurnVerdict], key_points: list[list[str]]) -> dict[str, float | None]:
    return {result.key: result.score for result in score_verdicts(verdicts, key_points)}


def test_coverage_counts_key_points_not_turns() -> None:
    # Pela média dos turnos daria 0,5; o turno de quatro pontos, todos cobertos, pesa mais que o de um
    # ponto que faltou.
    verdicts = [_verdict([True, True, True, True]), _verdict([False])]
    key_points = [["a", "b", "c", "d"], ["e"]]

    assert _scores(verdicts, key_points)["key_point_coverage"] == pytest.approx(0.8)


def test_missing_key_point_is_not_a_factual_error() -> None:
    # Deixar um ponto de fora e afirmar algo errado são defeitos diferentes: misturá-los numa nota só
    # reprovava respostas certas e incompletas como se estivessem erradas.
    scores = _scores([_verdict([True, False])], [["a", "b"]])

    assert scores["key_point_coverage"] == pytest.approx(0.5)
    assert scores["factual_accuracy"] == 1.0


def test_factual_error_fails_even_with_full_coverage() -> None:
    scores = _scores([_verdict([True, True], factual_accuracy=False)], [["a", "b"]])

    assert scores["key_point_coverage"] == 1.0
    assert scores["factual_accuracy"] == 0.0


def test_uncovered_key_point_is_named_in_the_comment() -> None:
    # Sem o ponto no comentário, quem lê o experimento sabe que faltou algo, mas não o quê.
    results = score_verdicts([_verdict([True, False])], [["usa colchetes", "mostra append"]])

    coverage = next(result for result in results if result.key == "key_point_coverage")
    assert coverage.comment is not None
    assert "mostra append" in coverage.comment
    assert "usa colchetes" not in coverage.comment
