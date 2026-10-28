# ADR 0002: Busca na documentação oficial com o gpt-5.4-mini

- **Status:** Aceita
- **Data:** 2026-10-28

## Contexto

Na linha de base, o `gpt-4.1-mini` errou todas as perguntas recentes do dataset (recursos do Python 3.12 ao 3.14 e a API do Pydantic v2): precisão factual 0,00 nelas, contra 0,90 no resto ([avaliação](../avaliacao.md#resultados)). O modelo não erra por omissão, mas afirmando o que era verdade antes do corte de treinamento: recomenda o `.dict()` do Pydantic v1 e diz que a biblioteca padrão não tem Zstandard. Um tutor que ensina com certeza uma resposta desatualizada é pior que um que não responde.

A ferramenta de busca web hospedada da OpenAI (`web_search`) roda nos servidores da OpenAI, dentro da mesma chamada ao modelo, e aceita um filtro de domínios. Duas restrições apareceram na prática: ela só existe na Responses API, e o `gpt-4.1-mini` recusa o filtro de domínios. Sem o filtro, a busca vai à web aberta, e qualquer página entra na resposta, inclusive uma com instruções escondidas para o modelo.

O experimento teve três braços na Responses API (`gpt-4.1-mini` sem busca, `gpt-5.4-mini` sem busca e com busca) e uma segunda rodada do `gpt-5.4-mini` com o prompt ajustado pelas falhas da primeira. Cada braço rodou uma vez, e as perguntas recentes são 5: cada uma pesa 0,20 na média delas.

| Segunda rodada | 5.4-mini sem busca | 5.4-mini com busca |
| --- | --- | --- |
| Precisão factual, recentes | 0,40 | 0,80 |
| Precisão factual, demais | 1,00 | 0,97 |
| Correção dos snippets | 0,87 | 0,94 |
| Custo p50, médio e p95 (US$ por mil turnos) | 3,06, 3,16 e 5,02 | 3,06, 4,93 e 18,27 |

## Decisão

- O padrão do chatbot é o `gpt-5.4-mini` com a busca ligada, pela Responses API.
- A busca fica restrita a domínios de documentação mantida pelo próprio projeto (`docs_search.py`), sem hospedagens abertas onde qualquer pessoa publica.
- O modelo decide quando buscar, guiado por uma regra do prompt: versão específica, recurso recente, biblioteca, ou se uma sintaxe existe. No básico da linguagem ele responde sem buscar.
- As páginas citadas pela busca aparecem no fim da resposta, como a OpenAI exige.
- Modelo e busca continuam configuráveis (`CHATBOT_MODEL` e `CHATBOT_DOCS_SEARCH`), e o `gpt-4.1-mini` sem busca segue disponível como opção barata.

## Alternativas consideradas

- **Manter o `gpt-4.1-mini` sem busca:** o mais barato (US$ 0,90 por mil turnos no p50) e o que responde mais completo no básico, mas erra todas as perguntas recentes, com certeza.
- **`gpt-4.1-mini` com busca aberta, pedindo os domínios oficiais no prompt:** mais barato que o `gpt-5.4-mini`, e o modelo de fato buscou no docs.python.org quando pedido. Mas nada garante o domínio, e a proteção contra conteúdo malicioso ficaria por conta do modelo obedecer ao prompt.
- **`gpt-5.4-mini` sem busca:** o modelo mais novo acerta sozinho o que é anterior ao corte de treinamento dele (genéricos do 3.12, Pydantic v2), mas erra as três perguntas do 3.14. Ganha do `gpt-4.1-mini` sem resolver o problema.
- **Ferramenta própria, lendo a documentação do Python direto (índice do Sphinx e API do PyPI):** custo por consulta menor e controle total, mas exige um laço de agente no nosso código, o modelo precisa saber o nome do que procura (e o recurso novo é justamente o que ele não conhece), e cada biblioteca fora do Sphinx pede tratamento próprio. Fica como caminho se a busca hospedada valer e custar demais.
- **Buscar em todo turno:** fecharia o caso em que o modelo não sabe que não sabe, a um custo médio perto de US$ 20 por mil turnos, cerca de quatro vezes o atual. Pagar a busca na pergunta sobre listas para fechar uma pergunta em cinco não se justifica sem saber quem são os usuários.

## Consequências

- **Precisão nas perguntas recentes:** vai de 0,00 para 0,80, com a fonte citada. As demais seguem praticamente intactas.
- **Custo:** o p50 sobe cerca de 3,4 vezes em relação ao `gpt-4.1-mini` (US$ 0,90 para US$ 3,06 por mil turnos), pelo modelo mais caro e pelas respostas mais longas. Os turnos com busca custam cerca de US$ 0,018, e o p95 vai a US$ 18. A latência p50 cai de 4,5 s para 3,3 s.
- **Limitação conhecida, o modelo que não sabe que não sabe:** a regra do prompt não fez o modelo buscar em "posso escrever `except ValueError, TypeError:`?", e ele respondeu com certeza que não pode (o 3.14 passou a aceitar). Ele só busca quando duvida. O próximo experimento é dizer ao modelo qual é a versão atual do Python e que o conhecimento dele pode estar desatualizado. Se não bastar, buscar em todo turno, com o custo acima.
- **Viés do juiz:** juiz (`gpt-5.4`) e chatbot (`gpt-5.4-mini`) passam a ser da mesma família, e o viés de autopreferência vira um risco a medir na calibração com rótulos humanos. O juiz também não conhece o 3.14: nas perguntas recentes, o que está fora dos pontos-chave é conferido pela execução dos snippets.
- **Sem LangGraph:** a busca hospedada não dispara o gatilho da [ADR 0001](0001-historico-explicito-sem-langgraph.md) para o LangGraph. Ela roda dentro da chamada ao modelo, sem laço de agente no nosso código, e o histórico continua numa lista explícita.
- **Dependência da OpenAI:** o chatbot fica preso a ela pela ferramenta hospedada e pela Responses API. Trocar de provedor pede outra busca, que pode ser a ferramenta própria.

## O que mudaria esta decisão em produção

Os números deste experimento medem o que cada configuração faz. Qual delas vale a pena depende do produto, e o teste técnico não diz:

- **Quem são os usuários:** iniciantes perguntam o básico, que o `gpt-4.1-mini` sem busca responde bem e mais barato. Usuários avançados perguntam o que é recente, onde a busca é a diferença entre certo e errado. A mistura real das perguntas define quanto pesa a precisão nas recentes.
- **O papel do bot:** como apoio dentro de um ecossistema com apostilas, professores e suporte, um erro do bot é corrigido por alguém, e a régua pode ser mais baixa. Como centro da aplicação, a resposta do bot é a resposta, e a régua sobe, talvez até buscar em todo turno.
- **Orçamento e qualidade exigida:** as metas das métricas, ainda "a definir" na [avaliação](../avaliacao.md#métricas), saem do orçamento por aluno e da qualidade que o produto exige. Com elas, a decisão vira uma conta: o custo por mil turnos de cada braço contra a precisão que cada um entrega na mistura real de perguntas.
- **O tamanho da amostra:** antes de virar meta, o efeito pede mais perguntas recentes no dataset e repetições de cada experimento, porque com 5 perguntas e uma execução, uma conversa muda a média em 0,20.
