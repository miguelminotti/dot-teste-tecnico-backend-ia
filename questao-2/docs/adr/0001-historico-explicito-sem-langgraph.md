# ADR 0001: Histórico da conversa numa lista explícita, sem LangGraph

- **Status:** Aceita
- **Data:** 2026-10-28

## Contexto

O enunciado pede que o LangChain gerencie o fluxo de conversação. Sem histórico, cada pergunta chega ao modelo sozinha: "e como removo um item dela?" não sabe de que lista se trata, e a oferta de aprofundar que o modelo faz no fim das respostas não tem como ser aceita. Num tutor, perguntar de novo e aprofundar é o uso normal.

Com histórico, cada turno reenvia a conversa inteira, e o custo de um turno cresce com o número de turnos. O cache de prompt da OpenAI barateia a parte da entrada que repete o começo de uma chamada recente, mas só se esse começo for idêntico byte a byte ([avaliação](../avaliacao.md#cache-de-prompt)).

No LangChain 1.x, as classes de histórico do `langchain-core` estão deprecadas: `RunnableWithMessageHistory` desde a 1.3.3, com a orientação de usar a persistência do LangGraph, e `BaseChatMessageHistory` e `InMemoryChatMessageHistory` desde a 1.6.4. As três saem na 2.0.

## Decisão

- O `Tutor` guarda os turnos numa lista de mensagens do LangChain (`HumanMessage` e `AIMessage`), que o prompt recebe por um `MessagesPlaceholder`.
- Uma instância do `Tutor` é uma conversa; a conversa vive enquanto o processo da CLI vive.
- A ordem do que vai ao modelo é fixa (sistema, turnos anteriores, pergunta nova) e o histórico só cresce no fim, para que cada chamada comece com exatamente o que a anterior enviou.
- Um turno só entra no histórico depois que o modelo responde.

## Alternativas consideradas

- **LangGraph com checkpointer:** é o caminho oficial de memória no LangChain 1.x e traz persistência pronta. Mas o fluxo é uma chamada ao modelo por turno, e um grafo de um nó só acrescentaria uma dependência e um conceito sem mudar o que vai ao modelo. A persistência que ele resolve não é necessária: a conversa da CLI não precisa sobreviver ao processo, nem atender vários usuários.
- **`RunnableWithMessageHistory`:** era a forma do LangChain de pôr histórico numa chain, mas está deprecado e sai na 2.0. Adotá-lo agora seria escrever código para ser reescrito.
- **Resumir ou cortar o histórico antigo:** limita o tamanho da entrada, mas muda o começo dela e zera o cache a cada resumo ou corte. Enquanto as conversas não se aproximarem do limite de contexto do modelo, não há o que limitar; quando a avaliação mostrar o custo de uma conversa longa, a troca entre tamanho e cache é decidida com números.

## Consequências

- O que vai ao modelo fica à vista no código, e os testes conferem com um modelo falso que cada chamada começa com tudo o que a anterior enviou.
- A avaliação monta uma conversa só criando um `Tutor` e fazendo as perguntas em ordem, sem configurar armazenamento.
- A conversa se perde quando a CLI fecha, e o histórico cresce sem limite durante a conversa.
- O LangGraph entra quando houver motivo medido ou um requisito que ele resolva: a ferramenta de consulta à documentação se provar útil nas avaliações (o `create_agent` do LangChain 1.x é montado sobre o LangGraph), a conversa precisar ser retomada depois, ou houver vários usuários ao mesmo tempo. Nesse dia, o histórico passa para o checkpointer, e o teste do prefixo continua valendo.
