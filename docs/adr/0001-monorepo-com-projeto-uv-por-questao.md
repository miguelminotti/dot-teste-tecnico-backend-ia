# ADR 0001: Um repositório para a prova, um projeto uv por questão

- **Status:** Aceita
- **Data:** 2026-10-27

## Contexto

A prova tem três questões independentes: uma API com FastAPI e SQLite, um chatbot com LangChain e OpenAI, e uma busca semântica com embeddings e FAISS. As dependências não se sobrepõem, e a terceira traz o torch, que pesa alguns gigabytes. Quem avalia precisa de um único lugar para ler o código e o histórico.

## Decisão

Um repositório git na raiz, com uma pasta por questão (`questao-1/`, `questao-2/`, `questao-3/`). Cada pasta é um projeto uv independente, com `pyproject.toml`, `uv.lock` e README próprios. Decisões que valem para todas as questões ficam em `docs/adr/` na raiz; as de uma questão só ficam em `questao-N/docs/adr/`.

## Alternativas consideradas

- **Um repositório por questão:** isola tudo, mas obriga o avaliador a abrir três links e perde a visão do histórico da prova inteira.
- **Um projeto uv único:** quem roda a questão 1 instalaria o torch da questão 3.
- **uv workspace:** resolve todas as questões num lockfile único, o que serve quando os pacotes dependem uns dos outros. Aqui não dependem, então o workspace só acoplaria versões.

## Consequências

- Cada questão roda sozinha com `uv sync` dentro da sua pasta.
- Ferramentas de qualidade são configuradas por questão, no `pyproject.toml` de cada uma (ver [ADR 0004](0004-qualidade-ruff-e-mypy-strict.md)).
- O `.gitignore` fica na raiz e vale para todas as questões, porque o `uv init` não cria um quando já existe git acima.
