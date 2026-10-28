# ADR 0001: Um repositório para a prova, um projeto uv por questão, todos em Python 3.12

- **Status:** Aceita
- **Data:** 2026-10-27

## Contexto

A prova tem três questões independentes: uma API com FastAPI e SQLite, um chatbot com LangChain e OpenAI, e uma busca semântica com embeddings e FAISS. As dependências não se sobrepõem, e a terceira traz o torch, que pesa alguns gigabytes. Quem avalia precisa de um único lugar para ler o código e o histórico.

FAISS e torch têm extensões nativas e costumam demorar a publicar wheels para versões novas do Python. Sem wheel, a instalação tenta compilar do código-fonte e quebra na máquina do avaliador.

## Decisão

- Um repositório git, com uma pasta por questão. Cada pasta é um projeto uv independente, com lockfile e README próprios.
- Decisões que valem para todas as questões ficam em `docs/adr/` na raiz; as de uma questão só ficam na pasta dela.
- Python 3.12 em todas as questões, fixado no projeto. O uv baixa essa versão sozinho se ela não estiver instalada.

## Alternativas consideradas

- **Um repositório por questão:** isola tudo, mas obriga o avaliador a abrir três links e perde a visão do histórico da prova inteira.
- **Um projeto uv único:** quem roda a questão 1 instalaria o torch da questão 3.
- **uv workspace:** resolve todas as questões num lockfile único, o que serve quando os pacotes dependem uns dos outros. Aqui não dependem, então o workspace só acoplaria versões.
- **Python mais novo (3.13 ou 3.14) nas questões 1 e 2:** cada questão rodaria num Python diferente, e um padrão de código válido numa poderia não valer na outra.

## Consequências

- Cada questão roda sozinha com `uv sync` dentro da sua pasta.
- Ferramentas de qualidade são configuradas por questão, cada uma no seu projeto.
- Subir a versão do Python exige conferir antes as wheels de FAISS e torch.
