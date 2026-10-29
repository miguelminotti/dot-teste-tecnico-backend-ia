import os
import subprocess
import sys
from collections.abc import Iterator

import pytest

from chatbot.cli import disable_tracing_without_key, run_chat
from chatbot.tutor import AnswerUnavailableError, OpenAIAccountError, RequestRejectedError

# Roda o laço da conversa com a configuração de terminal do `main`, mas com uma resposta fixa no lugar
# do modelo: o teste não depende de chave nem de rede.
_CHAT_WITH_ECHO = (
    "from chatbot.cli import run_chat, use_utf8_stdio; "
    "use_utf8_stdio(); "
    "run_chat(lambda question: 'recebi a pergunta: ' + question)"
)


def test_piped_accented_question_reaches_the_answer_intact() -> None:
    # Com a entrada redirecionada, o Python no Windows lê em cp1252, e "Olá" chegaria ao modelo como
    # "OlÃ¡". O processo roda de verdade, porque o bug está no encoding do stdin e stdout reais.
    # PYTHONIOENCODING=cp1252 reproduz o padrão do Windows em qualquer sistema operacional.
    env = {key: value for key, value in os.environ.items() if key != "PYTHONUTF8"}
    env["PYTHONIOENCODING"] = "cp1252"

    result = subprocess.run(
        [sys.executable, "-c", _CHAT_WITH_ECHO],
        input="Olá, é possível?\nsair\n".encode(),
        capture_output=True,
        env=env,
        check=True,
        timeout=30,
    )

    output = result.stdout.decode("utf-8")
    assert "recebi a pergunta: Olá, é possível?" in output
    assert "Até logo!" in output


def test_tracing_without_langsmith_key_is_turned_off() -> None:
    # O .env.example vem com o tracing ligado. Sem a chave do LangSmith, cada turno despejava avisos e
    # erros 401 no meio da conversa; quem só quer conversar não precisa do LangSmith.
    environ = {"LANGSMITH_TRACING": "true", "LANGSMITH_API_KEY": ""}

    assert disable_tracing_without_key(environ) is True
    assert environ["LANGSMITH_TRACING"] == "false"


def test_tracing_with_langsmith_key_is_kept() -> None:
    environ = {"LANGSMITH_TRACING": "true", "LANGSMITH_API_KEY": "chave"}

    assert disable_tracing_without_key(environ) is False
    assert environ["LANGSMITH_TRACING"] == "true"


class _FakeTerminal:
    """Entrada com respostas prontas e saída gravada, no lugar do `input` e do `print`."""

    def __init__(self, *lines: str) -> None:
        self._lines = list(lines)
        self.written: list[str] = []

    def read(self, _: str) -> str:
        if not self._lines:
            raise EOFError
        return self._lines.pop(0)

    def write(self, text: str) -> None:
        self.written.append(text)


def test_blank_question_does_not_reach_the_model_and_exit_words_end_the_chat() -> None:
    # Pergunta em branco viraria uma chamada paga sem pergunta; "SAIR" em maiúsculas também encerra.
    terminal = _FakeTerminal("   ", "Como criar uma lista?", "SAIR", "pergunta depois de sair")
    asked: list[str] = []

    def answer(question: str) -> str:
        asked.append(question)
        return "resposta"

    run_chat(answer, read=terminal.read, write=terminal.write)

    assert asked == ["Como criar uma lista?"]


def test_passing_failure_loses_only_that_question() -> None:
    # Uma falha passageira da API (rede, limite por minuto) não encerra a conversa.
    terminal = _FakeTerminal("pergunta que falha", "pergunta seguinte")
    replies: Iterator[str | Exception] = iter([AnswerUnavailableError("o modelo não respondeu"), "resposta"])

    def answer(_: str) -> str:
        reply = next(replies)
        if isinstance(reply, Exception):
            raise reply
        return reply

    run_chat(answer, read=terminal.read, write=terminal.write)

    assert "\nChatbot: resposta" in terminal.written


def test_request_the_api_will_always_reject_ends_the_chat() -> None:
    # Modelo sem acesso ou contexto estourado: repetir a pergunta dá o mesmo erro. A conversa acaba, e o
    # `main` sai com a mensagem da API.
    terminal = _FakeTerminal("primeira pergunta", "segunda pergunta")
    asked: list[str] = []

    def answer(question: str) -> str:
        asked.append(question)
        raise RequestRejectedError("o modelo não existe")

    with pytest.raises(RequestRejectedError):
        run_chat(answer, read=terminal.read, write=terminal.write)
    assert asked == ["primeira pergunta"]


def test_rejected_key_or_account_ends_the_chat() -> None:
    # Com a chave recusada, toda pergunta falharia: a conversa acaba, e o erro chega ao `main`, que sai
    # com a mensagem de configuração e código 1.
    terminal = _FakeTerminal("primeira pergunta", "segunda pergunta")
    asked: list[str] = []

    def answer(question: str) -> str:
        asked.append(question)
        raise OpenAIAccountError("a OpenAI recusou a chave")

    with pytest.raises(OpenAIAccountError):
        run_chat(answer, read=terminal.read, write=terminal.write)
    assert asked == ["primeira pergunta"]
