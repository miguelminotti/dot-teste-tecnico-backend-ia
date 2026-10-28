# Questão 2 - Chatbot de dúvidas de Python

Chatbot que responde perguntas sobre programação em Python, com LangChain e um modelo da OpenAI.

## Enunciado × status

| Requisito do enunciado | Status |
| --- | --- |
| Receber perguntas do usuário por input de texto | linha de comando (`uv run chatbot`) |
| Usar o LangChain para gerenciar a conversa e integrar com o LLM | pendente |
| Responder com um modelo da OpenAI (como o GPT-4) | pendente |
| Configuração da API da OpenAI | pendente |
| Exemplo "Como criar uma lista em Python?" com explicação detalhada | pendente |
| Exemplos de perguntas e respostas | pendente |

## Como rodar

Pré-requisito: [uv](https://docs.astral.sh/uv/). O uv baixa o Python 3.12 sozinho se ele não estiver instalado.

```bash
uv sync
```

Conversar com o chatbot (para sair, `sair` ou Ctrl+C):

```bash
uv run chatbot
```

Os comandos de qualidade (ruff, mypy) e as convenções do código estão no [README da raiz](../README.md).

## Decisões

- **Interface por linha de comando.** O enunciado pede input de texto e não pede front-end. Uma API ou uma interface web seria uma camada a mais sem requisito que a justifique. O laço da conversa recebe quem responde como parâmetro, então trocar a interface não mexe no chatbot.
- **Pergunta em branco não chega ao modelo.** Cada chamada ao LLM é paga; uma linha vazia (Enter sem querer) só pede a pergunta de novo.
