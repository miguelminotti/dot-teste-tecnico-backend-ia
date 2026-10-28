# Questão 2 - Chatbot de dúvidas de Python

Chatbot que responde perguntas sobre programação em Python, com LangChain e um modelo da OpenAI.

## Enunciado × status

| Requisito do enunciado | Status |
| --- | --- |
| Receber perguntas do usuário por input de texto | linha de comando (`uv run chatbot`) |
| Usar o LangChain para gerenciar a conversa e integrar com o LLM | prompt, modelo e extração do texto encadeados com LCEL, com o histórico da conversa e, opcional, a busca na documentação oficial |
| Responder com um modelo da OpenAI (como o GPT-4) | `gpt-5.4-mini` com busca na documentação oficial, escolhido pelas avaliações ([ADR 0002](docs/adr/0002-busca-na-documentacao-com-gpt-5-4-mini.md)); configurável |
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

O experimento usa o modelo de `CHATBOT_MODEL` e, com `CHATBOT_DOCS_SEARCH=true`, a busca na documentação; as variáveis podem vir na linha de comando para comparar configurações sem editar o `.env`.

## Decisões

- **Interface por linha de comando.** O enunciado pede input de texto e não pede front-end. Uma API ou uma interface web seria uma camada a mais sem requisito que a justifique. O laço da conversa recebe quem responde como parâmetro, então trocar a interface não mexe no chatbot.
- **Pergunta em branco não chega ao modelo.** Cada chamada ao LLM é paga; uma linha vazia (Enter sem querer) só pede a pergunta de novo.
- **`langchain-core` e `langchain-openai`, sem o pacote `langchain`.** O fluxo é prompt, modelo e parser encadeados (LCEL), que estão no `langchain-core`. O pacote `langchain` 1.x é montado sobre o LangGraph, para agentes com ferramentas, e traria o LangGraph junto sem uso. A busca na documentação não mudou isso: ela roda nos servidores da OpenAI, dentro da mesma chamada ao modelo, sem laço de agente no nosso código.
- **Histórico numa lista explícita, sem LangGraph.** O chatbot lembra os turnos anteriores, para que o aluno possa aprofundar ("e como removo um item dela?"). As classes de histórico do LangChain 1.x estão deprecadas em favor da persistência do LangGraph, mas um grafo para uma chamada por turno, numa conversa que vive só enquanto a CLI está aberta, seria uma camada sem uso. A lista também deixa à vista o que vai ao modelo, e o cache de prompt depende de cada chamada começar exatamente como a anterior. ([ADR 0001](docs/adr/0001-historico-explicito-sem-langgraph.md))
- **Prompt mínimo, com regras que vêm das avaliações.** Começou com papel, idioma, explicação detalhada com código em blocos ` ```python ` e recusa fora de Python. Cada regra seguinte entrou por uma falha medida: explicar o essencial na própria resposta (o modelo deixava o básico como oferta para depois), saída do programa em blocos ` ```text ` (ia em ` ```python ` e contava como código quebrado) e, com a busca ligada, buscar também quando a pergunta é se uma sintaxe existe. Os resultados de cada regra estão em [`docs/avaliacao.md`](docs/avaliacao.md#resultados).
- **`gpt-5.4-mini` com busca, escolhido pelas avaliações.** O ponto de partida foi o `gpt-4.1-mini`, da família do GPT-4 que o enunciado cita: barato e completo no básico, mas com precisão zero nas perguntas sobre recursos recentes do Python, e sem aceitar a busca restrita a domínios oficiais. Com o `gpt-5.4-mini` e a busca, a precisão nas recentes foi a 0,80, a um custo p50 cerca de 3,4 vezes maior (US$ 3,06 por mil turnos). O que mudaria a escolha num produto real (quem são os usuários, o papel do bot, orçamento e qualidade exigida) e a limitação que sobrou estão na [ADR 0002](docs/adr/0002-busca-na-documentacao-com-gpt-5-4-mini.md).
- **Busca na documentação oficial pela ferramenta hospedada da OpenAI, restrita a domínios oficiais.** Ligada por padrão; desliga com `CHATBOT_DOCS_SEARCH=false`. A busca roda nos servidores da OpenAI, então não há ferramenta nossa para manter nem laço de agente; o filtro de domínios (`docs_search.py`) deixa de fora hospedagens abertas, onde qualquer pessoa publica uma página com instruções escondidas para o modelo. O modelo busca só quando a pergunta envolve versão, recurso recente ou biblioteca, e as páginas citadas aparecem no fim da resposta, como a OpenAI exige. Uma ferramenta própria, lendo a documentação do Python direto, ficou como alternativa se a busca valer e custar demais.
- **Responses API.** A busca hospedada só existe nela, e o chatbot usa a mesma API com e sem busca, para que a comparação meça só a busca.
- **Falha da API perde a pergunta, não a conversa.** O cliente da OpenAI já repete as falhas passageiras; se mesmo assim não houver resposta, a CLI avisa e espera a próxima pergunta.
- **Chave conferida na subida.** Sem `OPENAI_API_KEY`, o chatbot sai com uma mensagem dizendo o que fazer, em vez de falhar na primeira pergunta com um erro de dentro da biblioteca.
