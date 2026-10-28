"""Roda um experimento no LangSmith: o tutor responde o dataset e os avaliadores medem as respostas.

Uso, na pasta da questão: uv run --env-file .env chatbot-eval
"""

import hashlib
import json
import os
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict
from pathlib import Path
from statistics import mean
from typing import Any

from langchain_core.callbacks import get_usage_metadata_callback
from langchain_openai import ChatOpenAI
from langsmith import Client, evaluate
from langsmith.evaluation import EvaluationResult, EvaluationResults
from langsmith.schemas import Example, Run

from chatbot.cli import use_utf8_stdio
from chatbot.evaluation.judge import CRITERIA, TurnVerdict, judge_turn
from chatbot.evaluation.snippets import SnippetStatus, run_answer_snippets
from chatbot.evaluation.usage import TurnUsage, cache_hit_rate, percentile, price_of, turn_cost
from chatbot.settings import Settings
from chatbot.tutor import Tutor

DATASET_PATH = Path("evals/dataset.json")
# Mais forte que o modelo do chatbot e de outra geração, para não favorecer o próprio estilo.
DEFAULT_JUDGE_MODEL = "gpt-5.4"
# Conversas avaliadas ao mesmo tempo; os turnos de uma conversa são sempre em sequência.
MAX_CONCURRENCY = 4


def sync_dataset(client: Client, path: Path) -> str:
    """Garante no LangSmith um dataset com o conteúdo exato do arquivo e devolve o nome dele.

    O nome leva o hash do arquivo: mudar o dataset cria outro, e cada experimento fica ligado à versão
    do dataset em que rodou, sem sobrescrever a anterior.
    """
    raw = path.read_bytes()
    name = f"dot-questao-2-{hashlib.sha256(raw).hexdigest()[:8]}"
    if client.has_dataset(dataset_name=name):
        return name
    conversations = json.loads(raw)
    dataset = client.create_dataset(name, description=f"Conversas de {path.as_posix()} (questão 2).")
    try:
        client.create_examples(
            dataset_id=dataset.id,
            examples=[
                {
                    "inputs": {"questions": [turn["question"] for turn in conversation["turns"]]},
                    "outputs": {"key_points": [turn["key_points"] for turn in conversation["turns"]]},
                    "metadata": {key: conversation[key] for key in ("id", "category", "python_version", "released_on")},
                }
                for conversation in conversations
            ],
        )
    except Exception:
        # Um dataset criado sem exemplos seria reaproveitado na próxima vez, vazio.
        client.delete_dataset(dataset_id=dataset.id)
        raise
    return name


def make_target(model: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def run_conversation(inputs: dict[str, Any]) -> dict[str, Any]:
        """Uma conversa nova por exemplo, com as perguntas feitas em ordem, como na CLI."""
        tutor = Tutor(ChatOpenAI(model=model))
        answers: list[str] = []
        turns: list[TurnUsage] = []
        for question in inputs["questions"]:
            with get_usage_metadata_callback() as usage_callback:
                started = time.perf_counter()
                answers.append(tutor.answer(question))
                latency = time.perf_counter() - started
            usages = usage_callback.usage_metadata.values()
            turns.append(
                TurnUsage(
                    input_tokens=sum(usage["input_tokens"] for usage in usages),
                    cache_read_tokens=sum(
                        usage.get("input_token_details", {}).get("cache_read", 0) for usage in usages
                    ),
                    output_tokens=sum(usage["output_tokens"] for usage in usages),
                    latency_seconds=latency,
                )
            )
        return {"answers": answers, "turns": [asdict(turn) for turn in turns]}

    return run_conversation


def make_judge_evaluator(judge_model: str) -> Callable[..., EvaluationResults]:
    judge = ChatOpenAI(model=judge_model)

    def judge_answers(
        inputs: dict[str, Any], outputs: dict[str, Any], reference_outputs: dict[str, Any]
    ) -> EvaluationResults:
        """Cobertura dos pontos-chave e fração dos turnos que passou em cada critério; o comentário traz as falhas."""
        verdicts = []
        previous: list[tuple[str, str]] = []
        for question, answer, key_points in zip(
            inputs["questions"], outputs["answers"], reference_outputs["key_points"], strict=True
        ):
            verdicts.append(
                judge_turn(judge, previous_turns=previous, question=question, key_points=key_points, answer=answer)
            )
            previous.append((question, answer))
        return EvaluationResults(results=score_verdicts(verdicts, reference_outputs["key_points"]))

    return judge_answers


def score_verdicts(verdicts: Sequence[TurnVerdict], key_points: Sequence[Sequence[str]]) -> list[EvaluationResult]:
    """Notas da conversa a partir dos vereditos de cada turno; o comentário de cada nota traz as falhas."""
    # Cobertura por ponto, e não por turno: um turno com quatro pontos pesa mais que um com um só.
    checks = [
        (number, point, check)
        for number, (verdict, points) in enumerate(zip(verdicts, key_points, strict=True), 1)
        for point, check in zip(points, verdict.key_points, strict=True)
    ]
    missing = [f"turno {number}: {point} ({check.reasoning})" for number, point, check in checks if not check.covered]
    results = [
        EvaluationResult(
            key="key_point_coverage",
            score=sum(check.covered for _, _, check in checks) / len(checks),
            comment="\n\n".join(missing) or None,
        )
    ]
    for criterion in CRITERIA:
        judged = [getattr(verdict, criterion) for verdict in verdicts]
        failures = [f"turno {number}: {item.reasoning}" for number, item in enumerate(judged, 1) if not item.passed]
        results.append(
            EvaluationResult(
                key=criterion,
                score=sum(item.passed for item in judged) / len(judged),
                comment="\n\n".join(failures) or None,
            )
        )
    return results


def evaluate_snippets(outputs: dict[str, Any], example: Example) -> EvaluationResults:
    """Fração dos snippets executados que rodou sem erro; os que dependem de pacote externo ficam de fora."""
    python_version = (example.metadata or {})["python_version"]
    results = [result for answer in outputs["answers"] for result in run_answer_snippets(answer, python_version)]
    executed = [result for result in results if result.status is not SnippetStatus.SKIPPED]
    failures = [result.detail for result in executed if result.status is SnippetStatus.FAILED]
    return EvaluationResults(
        results=[
            EvaluationResult(
                key="snippets_pass_rate",
                # Sem snippet executado não há taxa: zero puniria a resposta que não precisava de código.
                score=(len(executed) - len(failures)) / len(executed) if executed else None,
                comment="\n".join(failures) or None,
            ),
            EvaluationResult(key="snippets_skipped", score=len(results) - len(executed)),
        ]
    )


def make_usage_evaluator(model: str) -> Callable[[dict[str, Any]], EvaluationResults]:
    price = price_of(model)

    def evaluate_usage(outputs: dict[str, Any]) -> EvaluationResults:
        turns = [TurnUsage(**turn) for turn in outputs["turns"]]
        return EvaluationResults(
            results=[
                EvaluationResult(
                    key="cost_per_1k_turns_usd", score=_per_thousand(mean(turn_cost(turn, price) for turn in turns))
                ),
                EvaluationResult(key="latency_per_turn_s", score=mean(turn.latency_seconds for turn in turns)),
                EvaluationResult(key="cache_hit_rate", score=cache_hit_rate(turns)),
            ]
        )

    return evaluate_usage


def make_usage_summary(model: str) -> Callable[[list[Run], list[Example]], EvaluationResults]:
    price = price_of(model)

    def summarize_usage(runs: list[Run], examples: list[Example]) -> EvaluationResults:
        """Percentis sobre todos os turnos do experimento, e não sobre as médias de cada conversa."""
        turns = [TurnUsage(**turn) for run in runs if run.outputs for turn in run.outputs["turns"]]
        costs = [_per_thousand(turn_cost(turn, price)) for turn in turns]
        latencies = [turn.latency_seconds for turn in turns]
        return EvaluationResults(
            results=[
                EvaluationResult(key="cost_per_1k_turns_usd_p50", score=percentile(costs, 0.5)),
                EvaluationResult(key="cost_per_1k_turns_usd_p95", score=percentile(costs, 0.95)),
                EvaluationResult(key="latency_per_turn_s_p50", score=percentile(latencies, 0.5)),
                EvaluationResult(key="latency_per_turn_s_p95", score=percentile(latencies, 0.95)),
                EvaluationResult(key="cache_hit_rate_overall", score=cache_hit_rate(turns)),
            ]
        )

    return summarize_usage


def _per_thousand(cost_per_turn: float) -> float:
    """Custo de mil turnos em US$.

    O LangSmith guarda as notas com quatro casas decimais: US$ 0,00112 por turno viraria 0,0011, um erro
    de 2%. Por mil turnos, o mesmo valor é 1,12, e a unidade conversa direto com a escala de alunos.
    """
    return cost_per_turn * 1000


def main() -> None:
    use_utf8_stdio()
    try:
        settings = Settings.from_env()
        if not os.environ.get("LANGSMITH_API_KEY", "").strip():
            raise ValueError("LANGSMITH_API_KEY não definida: a avaliação roda no LangSmith")
        price_of(settings.model)
    except ValueError as error:
        sys.exit(f"Erro de configuração: {error}")
    judge_model = os.environ.get("EVAL_JUDGE_MODEL", "").strip() or DEFAULT_JUDGE_MODEL

    client = Client()
    dataset = sync_dataset(client, DATASET_PATH)
    evaluate(
        make_target(settings.model),
        data=dataset,
        evaluators=[make_judge_evaluator(judge_model), evaluate_snippets, make_usage_evaluator(settings.model)],
        summary_evaluators=[make_usage_summary(settings.model)],
        experiment_prefix=settings.model,
        metadata={"chatbot_model": settings.model, "judge_model": judge_model},
        max_concurrency=MAX_CONCURRENCY,
        client=client,
    )
