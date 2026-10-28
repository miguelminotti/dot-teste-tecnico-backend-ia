from pathlib import Path
from typing import Any, cast

import pytest
from langsmith import Client

from chatbot.evaluation.run import dataset_name, make_usage_summary, sync_dataset


def test_dataset_name_does_not_depend_on_line_endings() -> None:
    # O git converte o final de linha no checkout conforme o sistema: o mesmo dataset no Windows (CRLF)
    # e no Linux (LF) viraria dois datasets no LangSmith, e os experimentos não se comparariam.
    content = '[\n  {"id": "lista-criar"}\n]\n'

    assert dataset_name(content.replace("\n", "\r\n").encode()) == dataset_name(content.encode())


class _InterruptedClient:
    """Cliente do LangSmith falso: cria o dataset e é interrompido ao enviar os exemplos."""

    def __init__(self) -> None:
        self.deleted: list[str] = []

    def has_dataset(self, *, dataset_name: str) -> bool:
        return False

    def create_dataset(self, name: str, **kwargs: Any) -> Any:
        return type("Dataset", (), {"id": "dataset-1"})()

    def create_examples(self, **kwargs: Any) -> None:
        raise KeyboardInterrupt

    def delete_dataset(self, *, dataset_id: str) -> None:
        self.deleted.append(dataset_id)


def test_interrupted_upload_does_not_leave_an_empty_dataset(tmp_path: Path) -> None:
    # Um Ctrl+C no meio do envio deixava o dataset criado e vazio. Como o nome já existe, a próxima
    # execução o reaproveitaria, e todo experimento rodaria sobre zero exemplos.
    path = tmp_path / "dataset.json"
    path.write_text(
        '[{"id": "a", "category": "basico", "python_version": "3.12", "released_on": null, '
        '"turns": [{"question": "q", "key_points": ["p"]}]}]',
        encoding="utf-8",
    )
    client = _InterruptedClient()

    with pytest.raises(KeyboardInterrupt):
        sync_dataset(cast(Client, client), path)

    assert client.deleted == ["dataset-1"]


def test_usage_summary_of_an_experiment_where_every_conversation_failed() -> None:
    # Com a API fora do ar, nenhuma conversa tem turnos; o resumo quebrava com lista vazia (percentil e
    # divisão por zero) e escondia o erro de verdade, que está em cada conversa.
    summary = make_usage_summary("gpt-5.4-mini")

    assert summary([], []).get("results") == []
