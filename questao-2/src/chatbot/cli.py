"""Interface de linha de comando: lê as perguntas do terminal e imprime as respostas."""

import io
import sys
from collections.abc import Callable

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
            write(f"\nChatbot: {answer(question)}")
    except (EOFError, KeyboardInterrupt):
        # Ctrl+C, inclusive no meio de uma resposta, e fim da entrada (Ctrl+D, ou Ctrl+Z e Enter no
        # Windows) encerram a conversa sem traceback.
        pass
    write("\nAté logo!")


def main() -> None:
    _use_utf8_stdio()
    run_chat(_placeholder_answer)


def _use_utf8_stdio() -> None:
    """Força UTF-8 na entrada e na saída do terminal.

    Com entrada ou saída redirecionada (pipe, arquivo), o Python no Windows usa a página de código do
    sistema (cp1252), e "Olá" chegaria ao modelo como "OlÃ¡". No console interativo já é UTF-8.
    """
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        # O `isinstance` deixa de fora streams trocados por outro objeto (captura de testes, por exemplo).
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")


def _placeholder_answer(question: str) -> str:
    # Provisório: o LLM entra no próximo passo, no lugar desta função.
    return f"(ainda sem modelo) recebi a pergunta: {question}"
