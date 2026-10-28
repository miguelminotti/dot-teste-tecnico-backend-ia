"""Interface de linha de comando: lê as perguntas do terminal e imprime as respostas."""

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
    run_chat(_placeholder_answer)


def _placeholder_answer(question: str) -> str:
    # Provisório: o LLM entra no próximo passo, no lugar desta função.
    return f"(ainda sem modelo) recebi a pergunta: {question}"
