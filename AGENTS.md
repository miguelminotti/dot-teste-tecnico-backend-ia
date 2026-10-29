# AGENTS.md

Guia para agentes de IA (e para quem usa um) que vão ler, avaliar ou mudar este repositório. Para pessoas, o ponto de partida é o [README](README.md).

## O que é

A resolução de uma prova técnica para desenvolvedor backend com foco em IA: três questões independentes, cada uma um projeto uv próprio em Python 3.12. O enunciado original (PDF) não está no repositório. Cada README de questão abre com uma tabela "Enunciado × status", que liga cada requisito ao código e ao documento que o atende.

| Pasta | Tema | Comando principal | Precisa de |
| --- | --- | --- | --- |
| [`questao-1/`](questao-1/README.md) | API de biblioteca virtual (FastAPI, SQLite) | `uv run library` | nada |
| [`questao-2/`](questao-2/README.md) | Chatbot de dúvidas de Python (LangChain, OpenAI) | `uv run --env-file .env chatbot` | `OPENAI_API_KEY` no `.env` |
| [`questao-3/`](questao-3/README.md) | Busca semântica (embeddings, FAISS) | `uv run semantic-search "consulta"` | gerar o índice antes (veja abaixo) |

## Para avaliar rápido

Por questão, nesta ordem:

1. **README da questão:** a tabela "Enunciado × status" e as decisões em resumo.
2. **`docs/adr/`:** as decisões difíceis de reverter, com as alternativas descartadas. As que valem para todas as questões estão em [`docs/adr/`](docs/adr/README.md) na raiz.
3. **Código em `src/`** e testes em `tests/`. Os testes protegem regras de negócio; o `docs/qualidade.md` das questões 1 e 2 diz quais e lista os bugs que eles pegaram.
4. **Documentos de apoio em `docs/`:** qualidade e bugs achados (questões 1 e 2), avaliação e experimentos com números medidos (questões 2 e 3), exemplos com saídas reais (questões 2 e 3).

O que o enunciado pede está nos passos 1 e 3. O resto vai além dele (a questão 1 lista os acréscimos em "Além do enunciado") e pode ser lido só onde interessar.

As questões 2 e 3 foram feitas guiadas por avaliação: o conjunto de avaliação veio antes da escolha do modelo, e cada escolha tem números em `docs/avaliacao.md` ou `docs/experimentos.md`. Os resultados por consulta da questão 3 ficam em `questao-3/evals/results/`.

## Rodar e verificar

Os comandos rodam de dentro da pasta da questão. `uv sync` instala tudo; o uv baixa o Python 3.12 se faltar.

Os quatro portões de qualidade, que passam nas três questões:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

Nenhum teste chama serviço pago ou a rede: a questão 2 usa um modelo falso nos testes, e a questão 3 usa vetores pequenos.

**Questão 3: o índice não está no git.** Antes de buscar, gere os embeddings e o índice FAISS:

```bash
uv run semantic-search-embed
uv run semantic-search-store
uv run semantic-search "como avaliar agentes de programação" --k 5
```

O primeiro comando baixa o `BAAI/bge-m3` (4,3 GB) e leva menos de 3 minutos com GPU NVIDIA, ou cerca de 85 minutos na CPU. Para um teste rápido sem GPU, `--model intfloat/multilingual-e5-base` nos três comandos baixa 1,1 GB e leva cerca de 22 minutos. Com a versão CUDA do PyTorch instalada à mão no `.venv`, todos os comandos precisam de `uv run --no-sync`: um `uv run` comum volta o PyTorch para a versão de CPU do `uv.lock` ([`docs/indexacao.md`](questao-3/docs/indexacao.md)).

## Regras para quem muda o código

- **Idioma:** identificadores em inglês; comentários, docstrings, mensagens, READMEs e ADRs em português. Markdown com um parágrafo por linha, sem quebra manual.
- **Testes protegem regras de negócio,** sem teste trivial. Bug ganha um teste que falha antes da correção. Depois de implementar uma regra, quebre-a de propósito e confira que a suíte falha.
- **Números citados nos docs são conferidos rodando código.** Quem muda o que gera um número atualiza o doc que o cita.
- **Decisão difícil de reverter vira ADR,** no formato da [raiz](docs/adr/README.md). ADR aceita não é editada para mudar a decisão: uma nova a substitui.
- **Segredos:** `.env` fica fora do git (há `.env.example` em cada questão). Não imprima o conteúdo de um `.env`.
- **Custos:** o chatbot (`chatbot`) e a avaliação da questão 2 (`chatbot-eval`) chamam a OpenAI e cobram por uso; a geração de consultas da questão 3 (`semantic-search-queries`) também. Não rode esses comandos sem que o usuário peça.
- **Commits** seguem Conventional Commits com o escopo da questão: `feat(questao-3): ...`.
