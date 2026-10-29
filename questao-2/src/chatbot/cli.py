"""Interface de linha de comando: lê as perguntas do terminal e imprime as respostas."""

import io
import os
import sys
from collections.abc import Callable, MutableMapping

from chatbot.settings import Settings
from chatbot.tutor import AnswerUnavailableError, OpenAIAccountError, create_tutor

# Palavras que encerram a conversa, comparadas sem diferenciar maiúsculas.
_EXIT_COMMANDS = frozenset({"sair", "exit", "quit"})


def run_chat(
    answer: Callable[[str], str],
    *,
    read: Callable[[str], str] = input,
    write: Callable[[str], None] = print,
) -> None:
    """Laço da conversa: lê uma pergunta, imprime a resposta e repete até o usuário sair.

    `answer` é quem responde a pergunta; o laço não sabe se é um LLM. `read` e `write` são
    injetáveis para que o laço seja testado sem terminal.
    """
    write("Pergunte sobre Python. Para sair, digite 'sair' ou tecle Ctrl+C.")
    try:
        while True:
            question = read("\nVocê: ").strip()
            if not question:
                # Pergunta em branco não vai adiante: viraria uma chamada paga ao modelo sem pergunta.
                continue
            if question.casefold() in _EXIT_COMMANDS:
                break
            try:
                write(f"\nChatbot: {answer(question)}")
            except AnswerUnavailableError as error:
                # Uma falha da API perde só esta pergunta, não a conversa.
                write(f"\nNão consegui responder agora: {error}. Tente de novo.")
    except (EOFError, KeyboardInterrupt):
        # Ctrl+C, inclusive no meio de uma resposta, e fim da entrada (Ctrl+D, ou Ctrl+Z e Enter no
        # Windows) encerram a conversa sem traceback.
        pass
    write("\nAté logo!")


def main() -> None:
    use_utf8_stdio()
    if disable_tracing_without_key():
        print("LangSmith desligado: LANGSMITH_API_KEY não definida.", file=sys.stderr)
    try:
        settings = Settings.from_env()
    except ValueError as error:
        # Mensagem no stderr e código de saída 1, sem traceback: é erro de configuração, não bug.
        sys.exit(f"Erro de configuração: {error}")
    tutor = create_tutor(settings)
    try:
        run_chat(tutor.answer)
    except OpenAIAccountError as error:
        # A subida só confere se a chave existe; se ela vale, só a primeira pergunta diz.
        sys.exit(f"Erro de configuração: {error}")


def disable_tracing_without_key(environ: MutableMapping[str, str] = os.environ) -> bool:
    """Desliga o tracing do LangSmith quando falta a chave dele; devolve se desligou.

    Com o tracing ligado e sem chave, a biblioteca do LangSmith imprime avisos e erros 401 a cada turno,
    no meio da conversa. O chatbot funciona sem o LangSmith, então a falta da chave não é erro.
    """
    tracing = environ.get("LANGSMITH_TRACING", "").strip().casefold() == "true"
    if tracing and not environ.get("LANGSMITH_API_KEY", "").strip():
        environ["LANGSMITH_TRACING"] = "false"
        return True
    return False


def use_utf8_stdio() -> None:
    """Força UTF-8 na entrada e na saída do terminal.

    Com entrada ou saída redirecionada (pipe, arquivo), o Python no Windows usa a página de código do
    sistema (cp1252), e "Olá" chegaria ao modelo como "OlÃ¡". No console interativo já é UTF-8.
    """
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        # O `isinstance` deixa de fora streams trocados por outro objeto (captura de testes, por exemplo).
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")
