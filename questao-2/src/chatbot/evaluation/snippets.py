"""Execução dos snippets das respostas, para a métrica de correção dos snippets."""

import functools
import os
import re
import subprocess
import sys
import tempfile
import textwrap
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

# Bloco ```python (ou ```py, ```python3, em qualquer caixa). Blocos de outras linguagens, de saída ou sem
# linguagem não são executados.
_PYTHON_BLOCK = re.compile(r"```(?:python3?|py)[ \t]*\r?\n(.*?)```", re.DOTALL | re.IGNORECASE)
_MISSING_MODULE = re.compile(r"ModuleNotFoundError: No module named '([\w.]+)'")

TIMEOUT_SECONDS = 10.0

# Único ambiente que o snippet recebe. O código vem do modelo: herdar o ambiente inteiro entregaria a
# ele as chaves da OpenAI e do LangSmith. SYSTEMROOT e TEMP são o mínimo para o Python subir no Windows;
# HOME e USERPROFILE dão a pasta do usuário ao `Path.home()`, que falharia sem elas.
_INHERITED_ENV = ("PATH", "SYSTEMROOT", "TEMP", "TMP", "HOME", "USERPROFILE")


class SnippetStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    # Importa um pacote fora da biblioteca padrão: não é executado e não conta como falha.
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class SnippetResult:
    status: SnippetStatus
    # Última linha do erro ("ZeroDivisionError: division by zero"); vazio quando passou.
    detail: str = ""


def extract_python_blocks(answer: str) -> list[str]:
    """Blocos de código Python da resposta, na ordem em que aparecem.

    O recuo comum sai: um bloco dentro de um item de lista vem recuado pelo markdown, não pelo código.
    """
    return [textwrap.dedent(block) for block in _PYTHON_BLOCK.findall(answer) if block.strip()]


def run_answer_snippets(answer: str, python_version: str, *, timeout: float = TIMEOUT_SECONDS) -> list[SnippetResult]:
    """Roda os blocos da resposta em sequência, como o aluno que acompanha a explicação.

    Cada bloco roda depois dos anteriores que passaram: a lista criada num bloco existe no seguinte.
    Rodar cada bloco sozinho contava como erro (`NameError`) o código certo que só continua o anterior.
    Um bloco que falhou fica de fora do que vem depois, para que um erro (até um mostrado de propósito)
    não derrube os blocos seguintes. Um bloco pulado por dependência externa também fica de fora, senão
    o `import` dele pularia todos os seguintes; o bloco que depois falha com `NameError`, por usar o que
    o bloco pulado definiu, é pulado também.
    """
    results = []
    context: list[str] = []
    skipped_before = False
    for block in extract_python_blocks(answer):
        result = run_snippet("\n".join([*context, block]), python_version, timeout=timeout)
        if result.status is SnippetStatus.FAILED and skipped_before and result.detail.startswith("NameError"):
            result = SnippetResult(SnippetStatus.SKIPPED, "depende de um bloco pulado")
        if result.status is SnippetStatus.PASSED:
            context.append(block)
        skipped_before = skipped_before or result.status is SnippetStatus.SKIPPED
        results.append(result)
    return results


def run_snippet(code: str, python_version: str, *, timeout: float = TIMEOUT_SECONDS) -> SnippetResult:
    """Roda o snippet sozinho, num processo isolado, na versão do Python pedida.

    Sem entrada (`input()` recebe fim de arquivo), num diretório temporário, em modo isolado (`-I`, que
    ignora variáveis `PYTHON*` e o diretório atual no `sys.path`) e com tempo limite.
    """
    with tempfile.TemporaryDirectory() as workdir:
        script = Path(workdir) / "snippet.py"
        script.write_text(code, encoding="utf-8")
        env = {name: os.environ[name] for name in _INHERITED_ENV if name in os.environ}
        try:
            completed = subprocess.run(
                # `-X utf8`: um snippet que imprime acento não pode falhar por causa da página de código
                # do Windows. Vai na linha de comando porque o `-I` ignora o PYTHONIOENCODING.
                [_interpreter(python_version), "-I", "-X", "utf8", str(script)],
                cwd=workdir,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                env=env,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return SnippetResult(SnippetStatus.FAILED, f"passou do tempo limite de {timeout:g} s")

    if completed.returncode == 0:
        return SnippetResult(SnippetStatus.PASSED)
    stderr = completed.stderr.decode("utf-8", errors="replace")
    missing = _MISSING_MODULE.search(stderr)
    if missing and missing.group(1).split(".")[0] not in sys.stdlib_module_names:
        return SnippetResult(SnippetStatus.SKIPPED, f"depende de {missing.group(1)}")
    lines = stderr.strip().splitlines()
    return SnippetResult(SnippetStatus.FAILED, lines[-1] if lines else f"código de saída {completed.returncode}")


@functools.cache
def _interpreter(python_version: str) -> str:
    """Caminho do Python da versão pedida, achado pelo uv, fora de qualquer ambiente virtual.

    `--system` porque, sem ele, o uv acha o `.venv` do projeto, e o snippet rodaria com as dependências
    do chatbot instaladas: um `import pydantic` passaria aqui e falharia na máquina do aluno. O snippet
    roda direto nesse executável, e não por `uv run`: no tempo limite, o processo morto é o próprio
    Python, e não um intermediário que deixaria o snippet rodando.
    """
    found = subprocess.run(["uv", "python", "find", "--system", python_version], capture_output=True, text=True)
    if found.returncode != 0:
        raise RuntimeError(f"Python {python_version} não encontrado; instale com: uv python install {python_version}")
    return found.stdout.strip()
