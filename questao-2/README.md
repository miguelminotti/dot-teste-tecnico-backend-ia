# Questão 2 - Chatbot de dúvidas de Python

Chatbot de linha de comando que responde dúvidas de Python com LangChain (LCEL) e um modelo da OpenAI, e lembra a conversa para a pergunta seguinte ("e como removo um item dela?").

## Enunciado × status

| Requisito do enunciado | Status |
| --- | --- |
| Receber perguntas do usuário por input de texto | linha de comando (`uv run --env-file .env chatbot`) |
| Usar o LangChain para gerenciar a conversa e integrar com o LLM | prompt, modelo e extração do texto encadeados com LCEL, com o histórico da conversa e a busca na documentação oficial |
| Responder com um modelo da OpenAI (como o GPT-4) | `gpt-5.4-mini` com busca na documentação oficial, escolhido pelas avaliações ([ADR 0002](docs/adr/0002-busca-na-documentacao-com-gpt-5-4-mini.md)); configurável |
| Configuração da API da OpenAI | `.env` com a chave, conferida na subida |
| Exemplo "Como criar uma lista em Python?" com explicação detalhada | resposta real da CLI em [`docs/exemplos.md`](docs/exemplos.md#como-criar-uma-lista-em-python-o-exemplo-do-enunciado), com a pergunta seguinte usando o histórico |
| Exemplos de perguntas e respostas | [`docs/exemplos.md`](docs/exemplos.md); o dataset da avaliação tem mais 15 conversas com os pontos-chave esperados |

## Como rodar

Pré-requisito: [uv](https://docs.astral.sh/uv/), que baixa o Python 3.12 se ele não estiver instalado.

```bash
uv sync
```

Copie o `.env.example` para `.env` e preencha `OPENAI_API_KEY` e, para registrar os turnos no LangSmith, `LANGSMITH_API_KEY`. Sem chave do LangSmith, o chatbot desliga o tracing e avisa na subida. Para sair da conversa, `sair` ou Ctrl+C.

```bash
uv run --env-file .env chatbot
```

Os comandos de qualidade (ruff, mypy, pytest) estão no [README da raiz](../README.md); os bugs encontrados, em [`docs/qualidade.md`](docs/qualidade.md).

## Avaliação

O modelo e cada regra do prompt foram escolhidos por avaliação no LangSmith: 15 conversas, um juiz LLM e a execução do código das respostas na versão do Python de cada pergunta. O `gpt-4.1-mini`, da família do GPT-4 que o enunciado cita, errou todas as perguntas sobre recursos recentes do Python (precisão 0,00); o `gpt-5.4-mini` com busca restrita à documentação oficial acertou 4 de 5 (0,80), ficou em 0,97 no resto e custa US$ 3,06 por mil turnos no p50. Ficou em aberto: perguntado se `except ValueError, TypeError:` é válido, sem citar versão, o modelo responde "não" sem buscar, e o 3.14 passou a aceitar. Métricas, resultados e limitações estão em [`docs/avaliacao.md`](docs/avaliacao.md).

Rodar um experimento (precisa da `LANGSMITH_API_KEY` e do Python 3.14, que o uv não baixa sozinho para esse uso; `CHATBOT_MODEL` e `CHATBOT_DOCS_SEARCH` escolhem a configuração):

```bash
uv python install 3.14
```

```bash
uv run --env-file .env chatbot-eval
```

## Decisões

- **Histórico numa lista explícita, sem LangGraph:** as classes de memória do LangChain 1.x estão deprecadas em favor do LangGraph, que seria uma camada sem uso numa conversa que vive só enquanto a CLI está aberta ([ADR 0001](docs/adr/0001-historico-explicito-sem-langgraph.md)).
- **`gpt-5.4-mini` com a busca hospedada da OpenAI, restrita a domínios oficiais:** a busca roda nos servidores da OpenAI, sem laço de agente no nosso código, e as páginas citadas aparecem no fim da resposta; desliga com `CHATBOT_DOCS_SEARCH=false` ([ADR 0002](docs/adr/0002-busca-na-documentacao-com-gpt-5-4-mini.md)).
- **`langchain-core` e `langchain-openai`, sem o pacote `langchain`:** o fluxo é LCEL, que está no core; o `langchain` 1.x traria o LangGraph junto sem uso.
- **Prompt mínimo:** cada regra além do papel, do idioma e da recusa fora de Python entrou por uma falha medida na avaliação.
- **Falhas:** chave ausente encerra na subida; chave recusada ou conta sem saldo encerra na primeira pergunta; falha passageira da API perde só a pergunta, não a conversa; pergunta em branco não chega ao modelo, porque cada chamada é paga.
