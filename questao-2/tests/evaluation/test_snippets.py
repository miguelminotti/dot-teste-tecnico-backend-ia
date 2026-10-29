import subprocess

import pytest

from chatbot.evaluation.snippets import SnippetStatus, extract_python_blocks, run_answer_snippets, run_snippet


def _python_installed(version: str) -> bool:
    found = subprocess.run(["uv", "python", "find", "--system", version], capture_output=True)
    return found.returncode == 0


def test_extracts_only_python_blocks_in_order() -> None:
    # Bloco de saída, de outra linguagem ou sem linguagem não é código para executar: rodá-lo contaria
    # como falha um texto que nunca foi código.
    answer = (
        "Crie assim:\n```python\nitens = [1, 2]\n```\n"
        "A saída:\n```\n[1, 2]\n```\n"
        "No terminal:\n```bash\npip install x\n```\n"
        "E também:\n```py\nprint(len([1]))\n```\n"
        "Vazio:\n```python\n\n```\n"
    )

    assert extract_python_blocks(answer) == ["itens = [1, 2]\n", "print(len([1]))\n"]


def test_snippet_that_runs_passes() -> None:
    assert run_snippet("print(sum([1, 2, 3]))", "3.12").status is SnippetStatus.PASSED


def test_snippet_that_raises_fails_with_the_error() -> None:
    result = run_snippet("print(1 / 0)", "3.12")

    assert result.status is SnippetStatus.FAILED
    assert result.detail == "ZeroDivisionError: division by zero"


def test_snippet_runs_on_the_requested_python_version() -> None:
    # Um snippet correto de recurso novo (t-strings do 3.14) falharia por sintaxe numa versão anterior,
    # sem estar errado.
    assert run_snippet("import sys\nassert sys.version_info[:2] == (3, 12)", "3.12").status is SnippetStatus.PASSED


def test_third_party_import_is_skipped_not_failed() -> None:
    # Pydantic não está no ambiente do snippet; contar isso como falha puniria a resposta certa sobre
    # uma biblioteca.
    result = run_snippet("from pydantic import BaseModel", "3.12")

    assert result.status is SnippetStatus.SKIPPED
    assert result.detail == "depende de pydantic"


# O `uv sync` instala só o 3.12 do projeto; o 3.14 é instalado à mão para o experimento (README). Sem ele,
# o teste não tem onde rodar, e falhar aqui acusaria a máquina, não o executor.
@pytest.mark.skipif(not _python_installed("3.14"), reason="sem Python 3.14; instale com: uv python install 3.14")
def test_module_removed_from_the_standard_library_is_a_failure() -> None:
    # O `cgi` saiu da biblioteca padrão no 3.13. Um modelo treinado em código antigo ainda o usa, e o
    # snippet quebra na versão nova: é erro do snippet, não dependência externa a pular.
    result = run_snippet("import cgi", "3.14")

    assert result.status is SnippetStatus.FAILED
    assert result.detail == "ModuleNotFoundError: No module named 'cgi'"


def test_snippet_that_hangs_fails_by_timeout() -> None:
    result = run_snippet("while True:\n    pass", "3.12", timeout=1)

    assert result.status is SnippetStatus.FAILED
    assert "tempo limite" in result.detail


def test_snippet_does_not_receive_the_api_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    # O código vem do modelo e roda nesta máquina: com o ambiente herdado, um snippet poderia ler (e
    # mandar para fora) as chaves da OpenAI e do LangSmith.
    monkeypatch.setenv("OPENAI_API_KEY", "chave-que-nao-pode-vazar")
    monkeypatch.setenv("LANGSMITH_API_KEY", "outra-chave")

    code = "import os\nassert 'OPENAI_API_KEY' not in os.environ\nassert 'LANGSMITH_API_KEY' not in os.environ"
    assert run_snippet(code, "3.12").status is SnippetStatus.PASSED


def test_snippet_that_prints_accents_passes() -> None:
    # No Windows, saída redirecionada usa cp1252 por padrão; um "ç" fora dela derrubaria o snippet.
    assert run_snippet("print('ação ✓')", "3.12").status is SnippetStatus.PASSED


def test_block_that_continues_the_previous_one_passes() -> None:
    # A resposta cria a lista num bloco e a usa no seguinte. Rodar cada bloco sozinho contava como erro
    # (`NameError`) o código certo, e a métrica media o formato da resposta, não o código.
    answer = "```python\nitens = [1, 2]\n```\nDepois:\n```python\nitens.append(3)\nprint(itens)\n```"

    assert [result.status for result in run_answer_snippets(answer, "3.12")] == [
        SnippetStatus.PASSED,
        SnippetStatus.PASSED,
    ]


def test_failed_block_does_not_break_the_following_ones() -> None:
    # Um bloco que mostra um erro de propósito (ou que está errado) não pode derrubar os blocos certos
    # que vêm depois dele.
    answer = "```python\n[1, 2].push(3)\n```\nO certo:\n```python\nitens = [1]\nitens.append(2)\n```"

    results = run_answer_snippets(answer, "3.12")

    assert [result.status for result in results] == [SnippetStatus.FAILED, SnippetStatus.PASSED]
    assert results[0].detail == "AttributeError: 'list' object has no attribute 'push'"


def test_block_that_needs_a_skipped_dependency_is_skipped_too() -> None:
    # O bloco que importa o Pydantic é pulado; o seguinte, que usa o `BaseModel`, falhava com
    # `NameError` e contava como código errado numa resposta certa sobre a biblioteca.
    answer = (
        "```python\nfrom pydantic import BaseModel\n```\n"
        "Depois:\n```python\nclass Pessoa(BaseModel):\n    nome: str\n```"
    )

    assert [result.status for result in run_answer_snippets(answer, "3.12")] == [
        SnippetStatus.SKIPPED,
        SnippetStatus.SKIPPED,
    ]


def test_language_tag_ignores_case_and_accepts_python3() -> None:
    # Um bloco marcado ```Python ou ```python3 é código Python; ficava fora da métrica sem aviso.
    answer = "```Python\na = 1\n```\n```python3\nb = 2\n```"

    assert extract_python_blocks(answer) == ["a = 1\n", "b = 2\n"]


def test_block_indented_inside_a_list_item_runs() -> None:
    # Num item de lista numerada, o bloco vem recuado; o recuo é do markdown, não do código, e o código
    # certo falhava com `IndentationError`.
    answer = "1. Crie a lista:\n   ```python\n   itens = [1, 2]\n   print(itens)\n   ```\n"

    assert [result.status for result in run_answer_snippets(answer, "3.12")] == [SnippetStatus.PASSED]


def test_independent_block_after_a_skipped_one_still_runs() -> None:
    # Um bloco pulado por dependência externa levava junto todos os seguintes, porque o `import` dele
    # vinha antes de cada um: o erro do bloco independente sumia da métrica.
    answer = "```python\nimport requests\n```\nOutra coisa:\n```python\nprint(1 / 0)\n```"

    results = run_answer_snippets(answer, "3.12")

    assert [result.status for result in results] == [SnippetStatus.SKIPPED, SnippetStatus.FAILED]
    assert results[1].detail == "ZeroDivisionError: division by zero"


def test_snippet_can_find_the_home_directory() -> None:
    # Sem a variável da pasta do usuário, `Path.home()` falha, e um exemplo certo de leitura de arquivo
    # contaria como erro. A pasta do usuário não é segredo; as chaves continuam de fora.
    assert run_snippet("from pathlib import Path\nprint(Path.home())", "3.12").status is SnippetStatus.PASSED
