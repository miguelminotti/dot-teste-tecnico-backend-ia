# Questão 1 - API de biblioteca virtual

API para cadastrar e consultar livros (título, autor, data de publicação e resumo), com FastAPI e SQLite.

## Enunciado × status

| Requisito do enunciado | Status |
| --- | --- |
| Cadastro de livros com título, autor, data de publicação e resumo | pendente |
| Consulta de livros por título ou autor | pendente |
| Implementação com Django, Flask ou FastAPI | FastAPI (pendente) |
| Endpoints claros e bem documentados | pendente |
| Armazenamento em SQLite | pendente |
| Testes unitários dos endpoints | pendente |

## Como rodar

Pré-requisito: [uv](https://docs.astral.sh/uv/). O uv baixa o Python 3.12 sozinho se ele não estiver instalado.

```bash
uv sync
```

Validação de estilo e de tipos:

```bash
uv run ruff check .
```

```bash
uv run ruff format --check .
```

```bash
uv run mypy
```

## Decisões

### Um repositório para a prova, um projeto uv por questão

As três questões ficam no mesmo repositório git, cada uma na sua pasta com `pyproject.toml` e `uv.lock` próprios. Um repositório só facilita a avaliação, com um link e um histórico. Projetos separados porque as dependências das questões não têm nada em comum: FastAPI aqui, LangChain e OpenAI na questão 2, FAISS e transformers (que trazem o torch) na questão 3. Juntar tudo num ambiente obrigaria quem roda a questão 1 a instalar o torch.

**Por que não um uv workspace:** o workspace resolve todas as questões num lockfile único, o que é útil quando os pacotes dependem uns dos outros. Aqui eles não dependem, então o workspace só acoplaria versões sem ganho.

### Layout `src` em vez de módulo solto

O projeto foi criado com `uv init --package`, que coloca o código em `src/biblioteca/` e o instala no ambiente como pacote. A alternativa (`uv init --app`) gera um `main.py` na raiz, mais simples, mas que deixa os testes importarem o código pelo diretório atual. Um teste pode passar localmente e o pacote estar quebrado. Com o `src`, testes, mypy e a aplicação importam o código do mesmo jeito.

### Python 3.12

Existem versões mais novas (3.13, 3.14), mas a 3.12 é a mais segura para as wheels de FAISS e torch da questão 3. A mesma versão nas três questões evita que cada uma rode num Python diferente, facilitando o uso.

### ruff com 120 colunas e conjunto enxuto de regras

O ruff faz lint e formatação numa ferramenta só, substituindo flake8, isort e black. Limite de 120 colunas. Regras ligadas:

| Código | Origem | Para que serve |
| --- | --- | --- |
| `E`, `W` | pycodestyle | estilo básico (PEP 8) |
| `F` | pyflakes | import não usado, nome indefinido |
| `I` | isort | ordem dos imports |
| `UP` | pyupgrade | sintaxe moderna para o Python alvo |
| `B` | flake8-bugbear | armadilhas comuns (argumento padrão mutável, por exemplo) |
| `SIM` | flake8-simplify | código que pode ser simplificado |

**Por que não `select = ["ALL"]`:** liga centenas de regras opinativas (docstring em toda função, que é particularmente desnecessário para o caso atual, proibição de `assert` nos testes) que gerariam ruído num projeto desse tamanho. O conjunto pode crescer se a necessidade surgir.

### mypy em modo `strict` desde o início

O `strict` exige anotação de tipos em todas as funções e recusa `Any` implícito, que ajuda bastante com a tipagem fraca da linguagem. Ele roda sobre `src/`.
