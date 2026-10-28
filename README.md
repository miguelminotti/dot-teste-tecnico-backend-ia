# Prova para desenvolvedor backend com foco em IA

Cada questão é uma pasta com um projeto uv próprio, README próprio e as suas ADRs.

| Questão | Tema |
| --- | --- |
| [Questão 1](questao-1/README.md) | API de biblioteca virtual com FastAPI e SQLite |

Para rodar uma questão, entre na pasta dela e siga o README. O único pré-requisito é o [uv](https://docs.astral.sh/uv/), que baixa o Python 3.12 sozinho.

## Decisões

As decisões que valem para todas as questões estão em [`docs/adr/`](docs/adr/README.md); as de cada questão, na pasta dela.

## Convenções

**Idioma.** Identificadores em inglês (classes, funções, variáveis, módulos e o contrato JSON das APIs), porque leem melhor ao lado das bibliotecas, que são todas em inglês. Comentários, docstrings, mensagens de erro, READMEs e ADRs em português, a língua do enunciado. A regra é não misturar idiomas dentro do código: `Book` com `title`, nunca `Livro` com `author`.

**Qualidade.** Toda mudança passa por:

```bash
uv run ruff check .
```

```bash
uv run ruff format --check .
```

```bash
uv run mypy
```

```bash
uv run pytest
```

- **ruff** faz lint e formatação numa ferramenta só, com 120 colunas e um conjunto enxuto de regras (pycodestyle, pyflakes, isort, pyupgrade, bugbear e simplify). `select = ["ALL"]` ficou de fora por ligar centenas de regras opinativas que só gerariam ruído num projeto deste tamanho.
- **mypy** em modo `strict`, sobre o código e também sobre os testes, porque teste sem tipo é código que ninguém confere.
- **Layout `src/`**: testes, mypy e aplicação importam o pacote instalado, nunca o diretório atual, então um teste não passa com o pacote quebrado.
