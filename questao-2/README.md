# Questão 2 - Chatbot de dúvidas de Python

Chatbot que responde perguntas sobre programação em Python, com LangChain e um modelo da OpenAI.

## Enunciado × status

| Requisito do enunciado | Status |
| --- | --- |
| Receber perguntas do usuário por input de texto | linha de comando (`uv run chatbot`) |
| Usar o LangChain para gerenciar a conversa e integrar com o LLM | prompt, modelo e parser encadeados com LCEL, com o histórico da conversa |
| Responder com um modelo da OpenAI (como o GPT-4) | `gpt-4.1-mini` como ponto de partida, configurável; a escolha final sai das avaliações |
| Configuração da API da OpenAI | `.env` com a chave, conferida na subida |
| Exemplo "Como criar uma lista em Python?" com explicação detalhada | pendente |
| Exemplos de perguntas e respostas | pendente |

## Como rodar

Pré-requisito: [uv](https://docs.astral.sh/uv/). O uv baixa o Python 3.12 sozinho se ele não estiver instalado.

```bash
uv sync
```

Copie o `.env.example` para `.env` e preencha `OPENAI_API_KEY` e, para registrar os turnos no LangSmith, `LANGSMITH_API_KEY`. Sem chave do LangSmith, use `LANGSMITH_TRACING=false`.

Conversar com o chatbot (para sair, `sair` ou Ctrl+C):

```bash
uv run --env-file .env chatbot
```

Os comandos de qualidade (ruff, mypy, pytest) e as convenções do código estão no [README da raiz](../README.md). O que os testes protegem e os bugs encontrados estão em [`docs/qualidade.md`](docs/qualidade.md).

## Avaliação

O chatbot é desenvolvido guiado por avaliação: dataset e métricas vieram antes do código que chama o modelo, e cada peça da arquitetura entra se melhorar as métricas. O dataset está em [`evals/dataset.json`](evals/dataset.json); as métricas, o porquê de cada uma e os resultados dos experimentos, em [`docs/avaliacao.md`](docs/avaliacao.md).

Rodar um experimento no LangSmith (precisa também de `LANGSMITH_API_KEY`):

```bash
uv run --env-file .env chatbot-eval
```

## Decisões

- **Interface por linha de comando.** O enunciado pede input de texto e não pede front-end. Uma API ou uma interface web seria uma camada a mais sem requisito que a justifique. O laço da conversa recebe quem responde como parâmetro, então trocar a interface não mexe no chatbot.
- **Pergunta em branco não chega ao modelo.** Cada chamada ao LLM é paga; uma linha vazia (Enter sem querer) só pede a pergunta de novo.
- **`langchain-core` e `langchain-openai`, sem o pacote `langchain`.** O fluxo é prompt, modelo e parser encadeados (LCEL), que estão no `langchain-core`. O pacote `langchain` 1.x é montado sobre o LangGraph, para agentes com ferramentas, e traria o LangGraph junto sem uso. Ele entra se a ferramenta de consulta à documentação mostrar valor nas avaliações.
- **Histórico numa lista explícita, sem LangGraph.** O chatbot lembra os turnos anteriores, para que o aluno possa aprofundar ("e como removo um item dela?"). As classes de histórico do LangChain 1.x estão deprecadas em favor da persistência do LangGraph, mas um grafo para uma chamada por turno, numa conversa que vive só enquanto a CLI está aberta, seria uma camada sem uso. A lista também deixa à vista o que vai ao modelo, e o cache de prompt depende de cada chamada começar exatamente como a anterior. ([ADR 0001](docs/adr/0001-historico-explicito-sem-langgraph.md))
- **Prompt de partida mínimo.** Papel, idioma, explicação detalhada com código em blocos ` ```python ` e recusa fora de Python. Regras como corrigir premissa falsa ou citar a versão do Python entram quando uma avaliação mostrar a falha que corrigem, para que cada regra tenha um motivo medido.
- **Modelo configurável, `gpt-4.1-mini` para começar.** É da família do GPT-4 que o enunciado cita, barato e sem raciocínio (responde mais rápido). Como o corte de treinamento é anterior ao Python 3.14, as perguntas recentes do dataset devem mostrar a diferença que a consulta à documentação faz. A escolha final sai da comparação com outros modelos nas avaliações.
- **Falha da API perde a pergunta, não a conversa.** O cliente da OpenAI já repete as falhas passageiras; se mesmo assim não houver resposta, a CLI avisa e espera a próxima pergunta.
- **Chave conferida na subida.** Sem `OPENAI_API_KEY`, o chatbot sai com uma mensagem dizendo o que fazer, em vez de falhar na primeira pergunta com um erro de dentro da biblioteca.
