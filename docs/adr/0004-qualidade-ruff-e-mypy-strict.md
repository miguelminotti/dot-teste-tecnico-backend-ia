# ADR 0004: Qualidade com ruff e mypy strict, sobre código e testes

- **Status:** Aceita
- **Data:** 2026-10-27

## Contexto

Python tem tipagem dinâmica, e erros de tipo só aparecem em tempo de execução. Ligar checagem de tipo estrita depois que o código cresce custa uma rodada inteira de correções; com o código vazio, não custa nada.

## Decisão

- **ruff** para lint e formatação numa ferramenta só (substitui flake8, isort e black), com limite de 120 colunas e estas regras:

  | Código | Origem | Para que serve |
  | --- | --- | --- |
  | `E`, `W` | pycodestyle | estilo básico (PEP 8) |
  | `F` | pyflakes | import não usado, nome indefinido |
  | `I` | isort | ordem dos imports |
  | `UP` | pyupgrade | sintaxe moderna para o Python alvo |
  | `B` | flake8-bugbear | armadilhas comuns (argumento padrão mutável, por exemplo) |
  | `SIM` | flake8-simplify | código que pode ser simplificado |

- **mypy** em modo `strict`, rodando sobre `src/` e `tests/`.
- O layout é `src/` (`uv init --package`): testes, mypy e aplicação importam o pacote instalado, nunca o diretório atual.

Toda mudança passa por `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` e `uv run pytest`.

## Alternativas consideradas

- **`select = ["ALL"]` no ruff:** liga centenas de regras opinativas (docstring em toda função, proibição de `assert` nos testes) que geram ruído num projeto deste tamanho. O conjunto cresce quando aparecer necessidade.
- **mypy só sobre `src/`:** teste sem tipo é código que ninguém confere.
- **Módulo solto na raiz (`uv init --app`):** os testes importariam o código pelo diretório atual, e um teste poderia passar com o pacote quebrado.

## Consequências

- Toda função, inclusive de teste, precisa de anotação de tipo.
- `# type: ignore` sem uso é erro no modo strict, então ignorar um tipo exige justificativa real.
