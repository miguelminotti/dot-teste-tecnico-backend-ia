# Avaliação da questão 2

O chatbot é construído por desenvolvimento guiado por avaliação (*evaluation-driven development*, Chip Huyen, *AI Engineering*, 2025): o dataset e as métricas vêm antes da arquitetura, e cada peça (modelo, prompt, ferramenta de documentação, LangGraph) só entra se melhorar uma métrica sem estourar as outras. Os experimentos rodam no LangSmith.

## Dataset

Fica em [`evals/dataset.json`](../evals/dataset.json), versionado junto com o código, e é enviado ao LangSmith, onde ficam os experimentos e o histórico dos resultados. O repositório é a fonte da verdade porque uma mudança no dataset passa por revisão no diff, como o código; editar direto no LangSmith deixaria o dataset mudar sem rastro no histórico do projeto.

Cada exemplo tem a pergunta e os **pontos-chave** que a resposta precisa cobrir, em vez de uma resposta completa de referência. Uma pergunta de programação tem muitas respostas certas, e um juiz que compara com um texto de referência penaliza a resposta correta que só foi escrita de outro jeito. Os pontos-chave dizem o que não pode faltar e deixam a forma livre.

| Categoria | O que testa |
| --- | --- |
| `basico` | o caso do enunciado ("Como criar uma lista em Python?") e dúvidas de quem está começando |
| `armadilha` | explicar o porquê de um comportamento que surpreende, não só a correção |
| `premissa-falsa` | corrigir a pergunta em vez de inventar um método que não existe |
| `intermediario` | conceitos que pedem exemplo e critério de quando usar |
| `recente` | recursos novos da linguagem, com versão mínima |
| `biblioteca` | API de biblioteca que mudou entre versões |
| `fora-do-escopo` | recusar com educação e trazer a conversa de volta para Python |

Dois campos servem às métricas:

- `released_on`: data de lançamento do recurso que a pergunta cobre. Comparada com o corte de treinamento do modelo, separa as perguntas que o modelo não tem como saber. É nelas que a comparação com e sem a ferramenta de documentação vai mostrar diferença.
- `python_version`: versão do Python em que os snippets da resposta são executados. Um snippet correto de t-string falha no 3.12 por erro de sintaxe, sem estar errado.

## Métricas

| Métrica | Como mede | Unidade | Meta |
| --- | --- | --- | --- |
| Custo do turno | tokens de entrada e de saída vezes o preço do modelo, a partir do trace do LangSmith | US$ por turno, p50 e p95 | a definir |
| Taxa de acerto do cache | tokens de entrada lidos do cache sobre o total de tokens de entrada (`input_token_details.cache_read` no `usage_metadata` do LangChain) | fração, por turno e somada na conversa | a definir |
| Latência do turno | tempo total da resposta e tempo até o primeiro token (este só com streaming) | segundos, p50 e p95 | a definir |
| Correção dos snippets | extrai os blocos ` ```python ` da resposta e roda cada um num processo separado, na `python_version` do exemplo, com tempo limite | fração dos snippets que rodam sem erro | a definir |
| Correção técnica (juiz) | a resposta cobre cada ponto-chave e não afirma nada errado | passa ou falha, por exemplo | a definir |
| Qualidade didática (juiz) | critérios abaixo | passa ou falha, por critério | a definir |

Critérios da qualidade didática, julgados um a um:

- **Responde à pergunta:** o que foi perguntado é respondido logo, sem desviar.
- **Passo a passo:** quando a resposta tem um procedimento, ele vem em etapas na ordem em que se faz.
- **Exemplos:** tem exemplo de código ou analogia que ajuda a entender, e não decorativo.
- **Nível de detalhe:** detalhada o bastante para quem está aprendendo entender, sem encher.
- **Idioma:** responde no idioma da pergunta.

"Passo a passo" e "exemplos" valem quando cabem: numa pergunta conceitual sem procedimento, o critério passa como não aplicável. Exigir analogia em toda resposta empurraria o modelo a forçar uma onde ela não ajuda.

### Cache de prompt

Com histórico, cada turno reenvia ao modelo a conversa inteira: o custo de um turno cresce com o número de turnos, e o da conversa cresce com o quadrado. O cache de prompt da OpenAI cobra mais barato a parte inicial da entrada que for idêntica à de uma chamada recente (no `gpt-4.1-mini`, US$ 0,10 em vez de US$ 0,40 por milhão de tokens). Ele é automático, mas só funciona sob três condições, e a métrica existe para conferir que elas valem:

- **Prefixo idêntico.** O cache casa pelo começo da entrada. O prompt de sistema vem primeiro e não muda, e o histórico só cresce no fim: resumir, cortar ou reescrever turnos antigos zera o cache dali em diante.
- **Tamanho mínimo.** Abaixo de cerca de 1.024 tokens nada é cacheado. Os primeiros turnos de uma conversa curta mostram taxa zero por construção, não por defeito.
- **Tempo.** Sem retenção estendida, o cache dura de 5 a 10 minutos sem uso. Um aluno que para para testar o código por mais tempo que isso volta sem cache.

A taxa é lida junto com o custo: o desconto do token cacheado varia entre modelos, e uma taxa alta num modelo caro pode custar mais que uma taxa baixa num barato.

### Como o juiz decide

- **Passa ou falha por critério, com a justificativa antes do veredito,** em vez de uma nota de 1 a 10. Notas numéricas oscilam entre execuções e entre juízes, e uma nota 6 não diz o que melhorar; um critério que falhou diz.
- **Correção separada de didática.** Uma resposta clara, bem exemplificada e errada não pode passar por ser bem escrita.
- **O juiz não é o modelo que responde,** para não favorecer o próprio estilo (viés de autopreferência). O modelo do juiz é escolhido junto com o do chatbot.
- **Viés de verbosidade.** Juízes tendem a preferir respostas mais longas. O custo, que cresce com os tokens de saída, é o contrapeso: o enunciado pede uma explicação detalhada, e as duas métricas juntas medem se o detalhe vale o que custa.
- **O juiz é calibrado antes de ser confiado:** uma parte das respostas é rotulada à mão, e a concordância com o juiz é medida. Um juiz que discorda de quem rotulou mede outra coisa.

### Execução dos snippets

- Cada snippet roda num processo separado, com o Python em modo isolado, num diretório temporário e com tempo limite. O código vem do modelo respondendo a perguntas do dataset, escritas por nós, e não de usuários; se o dataset passar a ter entradas de fora, a execução vai para um container.
- Snippet que importa pacote fora da biblioteca padrão (o Pydantic, por exemplo) não é executado e é contado à parte, sem contar como falha.
- Snippet que mostra um erro de propósito (o `AttributeError` de chamar `push`) e snippet que lê do teclado com `input()` falham hoje. O primeiro resultado vai mostrar se são frequentes o bastante para pedir tratamento.

## Deixado de fora

- **Similaridade com uma resposta de referência (BLEU, ROUGE ou embeddings).** Mede o quanto a resposta se parece com um texto, não se ela está certa e ensina bem; numa resposta aberta, duas explicações corretas podem ter pouca sobreposição.
- **Conversa de vários turnos.** O chatbot já guarda o histórico ([ADR 0001](adr/0001-historico-explicito-sem-langgraph.md)), mas o dataset ainda tem um turno por exemplo. As conversas com aprofundamento, longas o bastante para passar do tamanho mínimo do cache, são o próximo passo do dataset; sem elas, a memória e a taxa de acerto do cache não têm o que medir.
