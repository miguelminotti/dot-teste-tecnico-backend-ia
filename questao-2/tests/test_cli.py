import os
import subprocess
import sys

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
