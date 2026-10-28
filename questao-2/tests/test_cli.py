import os
import subprocess
import sys


def test_piped_accented_question_reaches_the_answer_intact() -> None:
    # Com a entrada redirecionada, o Python no Windows lê em cp1252, e "Olá" chegaria ao modelo como
    # "OlÃ¡". O processo roda de verdade, porque o bug está no encoding do stdin e stdout reais.
    # PYTHONIOENCODING=cp1252 reproduz o padrão do Windows em qualquer sistema operacional.
    env = {key: value for key, value in os.environ.items() if key != "PYTHONUTF8"}
    env["PYTHONIOENCODING"] = "cp1252"

    result = subprocess.run(
        [sys.executable, "-c", "from chatbot.cli import main; main()"],
        input="Olá, é possível?\nsair\n".encode(),
        capture_output=True,
        env=env,
        check=True,
        timeout=30,
    )

    output = result.stdout.decode("utf-8")
    assert "recebi a pergunta: Olá, é possível?" in output
    assert "Até logo!" in output
