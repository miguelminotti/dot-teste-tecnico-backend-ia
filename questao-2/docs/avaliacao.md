# Avaliação da questão 2

O chatbot é construído por desenvolvimento guiado por avaliação (*evaluation-driven development*, Chip Huyen, *AI Engineering*, 2025): o dataset e as métricas vêm antes da arquitetura, e cada peça (modelo, prompt, ferramenta de documentação, LangGraph) só entra se melhorar uma métrica sem estourar as outras. Os experimentos rodam no LangSmith.

## Como rodar

Com `OPENAI_API_KEY` e `LANGSMITH_API_KEY` no `.env`, na pasta da questão:

```bash
uv run --env-file .env chatbot-eval
```

As perguntas do Python 3.14 pedem esse Python instalado (`uv python install 3.14`), porque os snippets rodam na versão de cada pergunta. O comando envia o dataset ao LangSmith (se esta versão ainda não estiver lá), faz o tutor responder cada conversa com o modelo de `CHATBOT_MODEL`, roda os avaliadores e imprime o link do experimento. O código está em `src/chatbot/evaluation/`.

Os braços de uma comparação mudam só as variáveis do chatbot, na linha de comando. O experimento da busca na documentação rodou assim:

```bash
CHATBOT_MODEL=gpt-4.1-mini CHATBOT_DOCS_SEARCH=false uv run --env-file .env chatbot-eval
CHATBOT_MODEL=gpt-5.4-mini CHATBOT_DOCS_SEARCH=false uv run --env-file .env chatbot-eval
CHATBOT_MODEL=gpt-5.4-mini CHATBOT_DOCS_SEARCH=true uv run --env-file .env chatbot-eval
```

## Dataset

Fica em [`evals/dataset.json`](../evals/dataset.json), versionado junto com o código. O repositório é a fonte da verdade porque uma mudança no dataset passa por revisão no diff, como o código; editar direto no LangSmith deixaria o dataset mudar sem rastro no histórico do projeto. No LangSmith, o nome do dataset leva o hash do arquivo, com o final de linha normalizado: mudar o arquivo cria um dataset novo, e cada experimento fica ligado à versão exata em que rodou. Os experimentos registrados abaixo rodaram em `dot-questao-2-a70fadc0`, com o hash do arquivo com CRLF do checkout no Windows; com a normalização, o mesmo conteúdo passa a se chamar `dot-questao-2-352e255e`, e o próximo experimento o cria.

Cada exemplo é uma **conversa**: uma lista de turnos, cada um com a pergunta e os **pontos-chave** que a resposta precisa cobrir. Uma pergunta solta é uma conversa de um turno. Os pontos-chave ficam no lugar de uma resposta completa de referência porque uma pergunta de programação tem muitas respostas certas, e um juiz que compara com um texto de referência penaliza a resposta correta escrita de outro jeito.

| Categoria | O que testa |
| --- | --- |
| `basico` | o caso do enunciado ("Como criar uma lista em Python?") e dúvidas de quem está começando |
| `armadilha` | explicar o porquê de um comportamento que surpreende, não só a correção |
| `premissa-falsa` | corrigir a pergunta em vez de inventar um método que não existe |
| `intermediario` | conceitos que pedem exemplo e critério de quando usar |
| `recente` | recursos novos da linguagem, com versão mínima |
| `biblioteca` | API de biblioteca que mudou entre versões |
| `fora-do-escopo` | recusar com educação e trazer a conversa de volta para Python |
| `conversa` | aprofundamento em vários turnos, com perguntas que só fazem sentido com o histórico ("e como removo um item dela?"), longas o bastante para passar do tamanho mínimo do cache |

Dois campos servem às métricas:

- `released_on`: data de lançamento do recurso que a pergunta cobre. Comparada com o corte de treinamento do modelo, separa as perguntas que o modelo não tem como saber. É nelas que a comparação com e sem a ferramenta de documentação vai mostrar diferença.
- `python_version`: versão do Python em que os snippets da resposta são executados. Um snippet correto de t-string falha no 3.12 por erro de sintaxe, sem estar errado.

## Métricas

| Métrica | Como mede | Unidade | Meta |
| --- | --- | --- | --- |
| Custo do turno | tokens de cada turno, lidos do uso das respostas do modelo, vezes a tabela de preços do código (`usage.py`), mais US$ 0,01 por busca na documentação | US$ por mil turnos, p50 e p95 | a definir |
| Uso da busca | fração dos turnos com ao menos uma busca na documentação (cada busca vem como um bloco `web_search_call` da resposta) | fração, por conversa e no experimento; lida por categoria | perto de 1 nas perguntas recentes, perto de 0 no resto |
| Taxa de acerto do cache | tokens de entrada lidos do cache sobre o total de tokens de entrada (`input_token_details.cache_read`), somados nos turnos | fração, por conversa e no experimento | a definir |
| Latência do turno | tempo da chamada ao `Tutor`, do envio ao fim da resposta | segundos, p50 e p95 | a definir |
| Correção dos snippets | extrai os blocos ` ```python ` da resposta e roda cada um, depois dos blocos anteriores da mesma resposta que passaram, num processo separado, na `python_version` do exemplo, com tempo limite | fração dos snippets executados que rodam sem erro | a definir |
| Cobertura dos pontos-chave (juiz) | o juiz diz, ponto a ponto, se a resposta transmite a ideia do ponto-chave | fração dos pontos cobertos na conversa | a definir |
| Precisão factual (juiz) | a resposta não afirma nada tecnicamente errado nem enganoso, inclusive no código; omissão não conta | fração dos turnos que passa | a definir |
| Qualidade didática (juiz) | critérios abaixo | fração dos turnos que passa, por critério | a definir |

Critérios da qualidade didática, cada um com veredito próprio:

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

- **Passa ou falha por critério, com a justificativa antes do veredito,** em vez de uma nota de 1 a 10. Notas numéricas oscilam entre execuções e entre juízes, e uma nota 6 não diz o que melhorar; um critério que falhou diz. A justificativa de cada falha fica no comentário do avaliador, no LangSmith.
- **Uma chamada do juiz por turno, com um veredito por critério.** Uma chamada por critério isolaria melhor um critério do outro, mas multiplicaria o custo por seis. Se a calibração mostrar um critério contaminando outro, eles se separam.
- **O juiz vê a conversa até ali,** para julgar uma resposta como "e como removo um item dela?" sabendo de que lista se fala.
- **Erro separado de omissão.** Afirmar algo errado é passa ou falha; deixar um ponto-chave de fora conta na cobertura, ponto a ponto. Na primeira linha de base, uma nota só ("cobre todos os pontos e não erra") reprovou 78% das respostas, muitas delas certas e incompletas, e não dizia qual dos dois defeitos a resposta tinha. A cobertura é contada por ponto, e não por turno, para que um turno de quatro pontos pese mais que um de um só.
- **Exemplo de ponto-chave é ilustração.** "Mostra o construtor `list()`, como `list(range(5))`" é coberto por `list("abc")`: o juiz é instruído a não exigir o exemplo literal.
- **Correção separada de didática.** Uma resposta clara, bem exemplificada e errada não pode passar por ser bem escrita.
- **O juiz não é o modelo que responde,** para não favorecer o próprio estilo (viés de autopreferência). O padrão é o `gpt-5.4`, mais forte que o do chatbot, configurável em `EVAL_JUDGE_MODEL`. Com o `gpt-5.4-mini` no chatbot, juiz e chatbot são da mesma família, e o viés de autopreferência volta a ser um risco a medir na calibração.
- **O juiz não conhece o que é mais novo que ele.** Nas perguntas recentes, o veredito só é confiável no que está nos pontos-chave, escritos por nós a partir da documentação; numa afirmação fora deles, o juiz pode reprovar código certo (aconteceu com o `flush()` do `compression.zstd`). Nesse caso, a execução dos snippets na versão certa do Python é quem decide.
- **Viés de verbosidade.** Juízes tendem a preferir respostas mais longas. O custo, que cresce com os tokens de saída, é o contrapeso: o enunciado pede uma explicação detalhada, e as duas métricas juntas medem se o detalhe vale o que custa.
- **O juiz precisa ser calibrado antes de ser confiado:** uma parte das respostas é rotulada à mão, e a concordância com o juiz é medida. Um juiz que discorda de quem rotulou mede outra coisa. A calibração ainda não foi feita: até ela, os vereditos do juiz são lidos junto com a execução dos snippets e com a leitura das falhas, uma a uma, como nos resultados abaixo.

### Execução dos snippets

- O código vem do modelo e roda nesta máquina, então o processo do snippet é restrito: Python fora de qualquer ambiente virtual (sem as dependências do chatbot), modo isolado (`-I`), diretório temporário, sem entrada, com tempo limite de 10 segundos e com um ambiente que só tem o necessário para o Python subir e achar a pasta do usuário, sem as chaves da OpenAI e do LangSmith. Restrito não é isolado: o snippet ainda lê o disco (inclusive o `.env`) e acessa a rede. O risco é baixo porque as perguntas são do dataset, escritas por nós, e as páginas que a busca traz são só de domínios oficiais; se o dataset passar a ter entradas de fora, a execução vai para um container sem rede.
- Snippet que importa pacote fora da biblioteca padrão (o Pydantic, por exemplo) não é executado e é contado à parte, sem contar como falha. Módulo da biblioteca padrão que não existe na versão do exemplo (o `cgi`, removido no 3.13) é falha.
- Os blocos podem vir recuados (dentro de um item de lista) e marcados como ` ```python `, ` ```py ` ou ` ```python3 `, em qualquer caixa; o recuo comum sai antes de rodar.
- A biblioteca padrão de referência é a do Python que roda a avaliação (3.12). Um módulo que só existe numa versão mais nova, ou um nome de módulo inventado pelo modelo, cai como dependência externa e é pulado, em vez de contar como falha. A correção técnica, julgada pelo juiz, cobre esse caso.
- **Os blocos de uma resposta rodam em sequência,** como o aluno que acompanha a explicação: cada bloco roda depois dos anteriores da mesma resposta que passaram, então a lista criada num bloco existe no seguinte. Na primeira linha de base, com cada bloco rodando sozinho, a maior parte das falhas era `NameError` de código certo que só continuava o anterior. Um bloco que falhou fica de fora do que vem depois, para que um erro não derrube os blocos certos seguintes. Um bloco pulado por dependência externa também fica de fora, senão o `import` dele pularia todos os blocos seguintes, inclusive os independentes; o bloco que depois falha com `NameError`, por usar o que o bloco pulado importou, é pulado também. Blocos de turnos diferentes não se juntam: cada resposta é avaliada pelo que ela mesma mostra.
- Snippet que mostra um erro de propósito (o `AttributeError` de chamar `push`) e snippet que lê do teclado com `input()` contam como falha.

## Resultados

A escolha que estes resultados sustentam, o `gpt-5.4-mini` com busca, e o que a mudaria num produto real estão na [ADR 0002](adr/0002-busca-na-documentacao-com-gpt-5-4-mini.md).

Os valores das tabelas são a média, entre as conversas, da nota de cada uma. "Perguntas recentes" são as categorias `recente` e `biblioteca` (5 conversas); "demais" são as outras 10. Cada experimento rodou uma vez: o mesmo modelo dá respostas diferentes a cada execução, e uma diferença pequena entre dois experimentos pode ser só isso.

### Segunda rodada: prompt ajustado pelas falhas da primeira (2026-10-28)

Três regras entraram no prompt, cada uma por uma falha medida na rodada anterior: explicar o essencial na própria resposta em vez de oferecer para depois (o exemplo do enunciado tinha caído para 0,50 de cobertura); pôr a saída do programa em blocos ```` ```text ````, e não ```` ```python ```` (era a maior parte das falhas de snippet do `gpt-5.4-mini`); e, só com a busca ligada, buscar também quando a pergunta é se uma sintaxe, função ou módulo existe ou é permitido (o caso do `except`). Rodaram de novo os dois braços do `gpt-5.4-mini`; o `gpt-4.1-mini` ficou de fora, porque não aceita a busca restrita.

Experimentos `gpt-5.4-mini-eaac41d6` (sem busca) e `gpt-5.4-mini-busca-599186b5` (com busca). Nenhuma conversa deu erro. Entre parênteses, o valor da primeira rodada.

| Métrica | 5.4-mini | 5.4-mini com busca |
| --- | --- | --- |
| Precisão factual, recentes | 0,40 (0,20) | **0,80** (0,60) |
| Cobertura, recentes | 0,39 (0,50) | 0,61 (0,65) |
| Precisão factual, demais | 1,00 (1,00) | 0,97 (1,00) |
| Cobertura, demais | 0,82 (0,74) | 0,79 (0,77) |
| Correção dos snippets, geral | 0,87 (0,76) | **0,94** (0,84) |
| Turnos com busca, recentes | – | 3 de 5 (2 de 5) |
| Turnos com busca, demais | – | 0 de 18 (0 de 18) |
| Custo p50 (US$ por mil turnos) | 3,06 (2,49) | 3,06 (3,11) |
| Custo médio | 3,16 (2,56) | 4,93 (4,58) |
| Custo p95 | 5,02 (4,72) | 18,27 (17,37) |
| Latência p50 | 3,5 s (2,7 s) | 3,3 s (2,2 s) |

O que a segunda rodada mostra:

- **O bloco de saída resolveu os snippets.** Sem a saída do programa rodando como código, a correção dos snippets foi a 0,87 e 0,94, acima do `gpt-4.1-mini` (0,91). No braço com busca, os snippets das perguntas recentes passaram todos.
- **O essencial na resposta encarece e ajuda pouco.** As respostas ficaram mais longas: o custo p50 sem busca subiu 23% e a latência p50 quase 1 s. A cobertura nas perguntas que não são recentes voltou ao nível do `gpt-4.1-mini` sem busca (0,82), mas o exemplo do enunciado deu 1,00 num braço e 0,50 no outro, com o mesmo prompt: a resposta ainda termina oferecendo o resto ("Se quiser, posso mostrar..."), e às vezes deixa de dizer que a lista é ordenada. Com uma execução por braço, a diferença entre os dois é ruído.
- **A busca segue sendo o que acerta as recentes, e agora acerta quatro de cinco.** Com ela, t-strings, `compression.zstd` e genéricos do 3.12 saem certos e com fonte; o modelo buscou também nos genéricos, que citam versão. Sem ela, as três do 3.14 erram.
- **A regra não fez o modelo buscar no `except`.** Ele não buscou, e de novo respondeu com certeza que a forma é inválida. Uma regra de prompt não resolve o caso em que o modelo não sabe que não sabe: a decisão de buscar é dele, e ele só busca quando duvida. Fechar esse caso pede outra coisa, como dizer ao modelo qual é a versão atual do Python e que o conhecimento dele pode estar desatualizado, ou buscar em todo turno (cerca de US$ 20 por mil turnos, quatro vezes o custo médio atual).
- **A única falha de precisão no resto é um caso de fronteira.** Em `conversa-indice`, o juiz reprovou `if indice < len(numeros):` como forma de evitar o `IndexError`, porque um índice negativo inválido passa pelo `if`. A crítica procede, e o critério "na dúvida falha" pega esse tipo de omissão.

### Busca na documentação: três braços na Responses API (2026-10-28)

A busca hospedada da OpenAI (`web_search`) só existe na Responses API, e o filtro que a restringe aos domínios oficiais não é aceito pelo `gpt-4.1-mini` (a API recusa a chamada). Por isso o experimento tem três braços, todos na Responses API, com o mesmo dataset e o mesmo juiz: o `gpt-4.1-mini` sem busca refaz a linha de base nessa API; o `gpt-5.4-mini` sem busca mede o efeito de trocar de modelo; o `gpt-5.4-mini` com busca mede o efeito da busca. Sem o braço do meio, o ganho do modelo mais novo seria atribuído à busca.

Experimentos `gpt-4.1-mini-6dbe9b20`, `gpt-5.4-mini-33439684` e `gpt-5.4-mini-busca-0e1e2950`. Nenhuma conversa deu erro.

| Perguntas recentes (5 conversas) | 4.1-mini | 5.4-mini | 5.4-mini com busca |
| --- | --- | --- | --- |
| Cobertura dos pontos-chave | 0,30 | 0,50 | 0,65 |
| Precisão factual | 0,00 | 0,20 | **0,60** |
| Responde à pergunta | 0,40 | 0,80 | 1,00 |
| Nível de detalhe | 1,00 | 0,80 | 1,00 |
| Correção dos snippets | 0,79 | 0,54 | 0,68 |
| Turnos com busca | – | – | 2 de 5 |

| Demais (10 conversas) | 4.1-mini | 5.4-mini | 5.4-mini com busca |
| --- | --- | --- | --- |
| Cobertura dos pontos-chave | **0,82** | 0,74 | 0,77 |
| Precisão factual | 1,00 | 1,00 | 1,00 |
| Responde à pergunta | 1,00 | 1,00 | 1,00 |
| Nível de detalhe | 0,90 | 1,00 | 1,00 |
| Correção dos snippets | 0,97 | 0,88 | 0,93 |
| Turnos com busca | – | – | 0 de 18 |

Passo a passo, exemplos e idioma ficaram em 1,00 nos três braços.

| Uso por turno | 4.1-mini | 5.4-mini | 5.4-mini com busca |
| --- | --- | --- | --- |
| Custo p50 (US$ por mil turnos) | 0,90 | 2,49 | 3,11 |
| Custo médio | 0,90 | 2,56 | 4,58 |
| Custo p95 | 1,61 | 4,72 | 17,37 |
| Latência p50 | 4,5 s | 2,7 s | 2,2 s |
| Latência p95 | 7,2 s | 6,0 s | 5,2 s |
| Acerto do cache | 0% | 13% | 58% |

O que o experimento mostra:

- **A busca é o que corrige as perguntas recentes.** A precisão nelas vai de 0,00 a 0,20 com o modelo novo e a 0,60 com a busca. O modelo novo sozinho acerta o que é anterior ao corte de treinamento dele (genéricos do 3.12 e `model_dump()` do Pydantic v2); as t-strings e o `compression.zstd` do 3.14 só saem certos com a busca, e com a página citada.
- **O modelo decide buscar só quando sabe que não sabe.** Buscou nas duas perguntas que citam o 3.14 e em nenhuma das 18 do resto, como a regra pede. Mas na pergunta "posso escrever `except ValueError, TypeError:`?", que não cita versão, ele respondeu "não" com confiança, sem buscar, e errou: o 3.14 passou a aceitar essa forma (PEP 758). É a falha que sobra, e a mais perigosa, porque é a resposta errada dita com certeza. Na CLI, a mesma pergunta com "no Python 3.14" dispara a busca e sai certa.
- **A busca pesa no custo da cauda, não no típico.** Um turno com busca custa cerca de US$ 0,018 (US$ 0,01 da chamada mais 8 a 9 mil tokens das páginas lidas), uns 7 vezes o turno sem busca do mesmo modelo. Com a busca só onde precisa, o p50 sobe 25% e o p95 quase quadruplica. Se a regra de quando buscar for alargada para pegar o caso do `except`, a conta muda: buscar em todo turno levaria o custo médio para perto de US$ 20 por mil turnos.
- **Trocar de modelo encarece e encurta as respostas.** O `gpt-5.4-mini` custa cerca de 2,8 vezes o `gpt-4.1-mini` no p50, é mais rápido (2,7 s contra 4,5 s) e responde mais curto, oferecendo o resto ("Se quiser, posso mostrar...") em vez de explicar. A cobertura nas perguntas que não são recentes cai de 0,82 para 0,74, e o exemplo do enunciado ("Como criar uma lista em Python?") cai de 1,00 para 0,50: a resposta não diz que a lista é ordenada e mutável e não mostra o `append`. O critério "nível de detalhe" passou essas respostas, o que é mais um sinal de que ele precisa de calibração.
- **A queda nos snippets do `gpt-5.4-mini` é de formato, não de código.** Ele põe a saída do programa num bloco ```` ```python ````, que o executor roda e falha com `SyntaxError`. Os erros de código de verdade foram poucos: no zstd com busca, `b"Olá, mundo!"` (bytes só aceitam ASCII).
- **O juiz também não conhece o 3.14.** No zstd com busca, ele reprovou a precisão dizendo que `ZstdCompressor` não tem `flush()`; o snippet com `flush()` roda no 3.14. A reprovação se sustenta pelo erro do `b"Olá"`, que ele não apontou. Nas perguntas recentes, o juiz só é confiável no que está nos pontos-chave, escritos por nós; o resto, quem confere é a execução dos snippets.
- **O cache não se compara entre os braços.** As conversas do dataset ficam perto do mínimo de 1.024 tokens: na de listas, o terceiro turno do `gpt-4.1-mini` teve 1.020 tokens, nada foi cacheado, e o braço deu 0%. Pequenas diferenças no tamanho das respostas mudam a taxa inteira. No braço com busca, as páginas lidas entram na conta e puxam a taxa para cima. A taxa só diz algo com conversas mais longas.
- **Cada braço rodou uma vez, e as perguntas recentes são 5.** Cada conversa vale 0,20 na média delas: a diferença entre 0,20 e 0,60 são duas conversas. A direção é clara (as duas do 3.14 com busca saíram certas, com fonte); o tamanho do efeito pede mais perguntas recentes e repetições antes de virar meta.

### Linha de base com as réguas ajustadas: `gpt-4.1-mini`, prompt mínimo (2026-10-28)

Experimento `gpt-4.1-mini-4e2c001d`, mesmo dataset, juiz `gpt-5.4`. Nenhuma conversa deu erro. É a referência para as próximas mudanças.

| Métrica | Geral | Perguntas recentes | Demais |
| --- | --- | --- | --- |
| Cobertura dos pontos-chave | 0,65 | 0,30 | 0,82 |
| Precisão factual | 0,60 | **0,00** | 0,90 |
| Responde à pergunta | 0,80 | 0,40 | 1,00 |
| Nível de detalhe | 0,73 | 0,40 | 0,90 |
| Passo a passo, exemplos e idioma | 1,00 | 1,00 | 1,00 |
| Correção dos snippets | 0,88 | 0,75 | 0,93 |

| Uso por turno | p50 | p95 |
| --- | --- | --- |
| Custo | US$ 0,85 por mil turnos | US$ 1,18 por mil turnos |
| Latência | 4,7 s | 7,5 s |

Taxa de acerto do cache no experimento: 38% dos tokens de entrada.

O que a linha de base mostra:

- **Nas perguntas recentes, toda resposta tem um erro factual,** não só uma omissão. O modelo recomenda o `.dict()` do Pydantic v1 como a forma de converter um modelo, e, nos genéricos do 3.12, apresenta `repeat[int](5, 3)`, que dá `TypeError`; o executor de snippets e o juiz pegaram esse erro cada um por um caminho. Nas três do 3.14, o modelo não conhece os recursos. É a lacuna que a ferramenta de consulta à documentação tem de fechar, agora medida.
- **No resto, a precisão é 0,90 e a cobertura 0,82.** A única falha de precisão é "lista vs tupla", por dizer que tupla pode ser chave de dicionário sem a ressalva de que os itens também precisam ser imutáveis. É um caso de fronteira, bom para a calibração do juiz.
- **As falhas de snippet que sobraram são de três tipos:** erro de verdade (o dos genéricos); erro mostrado de propósito (`IndexError` e `KeyError` para ensinar o erro), que derruba também os blocos seguintes que usavam a variável criada nele; e código que usa uma variável de um turno anterior. As de Pydantic eram um bug da régua, corrigido depois deste experimento (bug 4 em [qualidade.md](qualidade.md)).
- **Passo a passo, exemplos e idioma continuam em 100%.** Só os rótulos humanos da calibração dizem se o tutor já cumpre ou se os critérios estão frouxos.

### Primeira linha de base: réguas antigas (2026-10-28)

Experimento `gpt-4.1-mini-139b9a27`, mantido como registro de por que as réguas mudaram. A correção técnica ainda era uma nota só (cobertura de todos os pontos e nenhum erro), os snippets rodavam cada um sozinho, e o custo era registrado por turno.

| Métrica | Geral | Perguntas recentes (5) | Demais (10) |
| --- | --- | --- | --- |
| Correção técnica | 0,22 | 0,00 | 0,33 |
| Responde à pergunta | 0,80 | 0,60 | 0,90 |
| Passo a passo | 1,00 | 1,00 | 1,00 |
| Exemplos | 1,00 | 1,00 | 1,00 |
| Nível de detalhe | 0,80 | 0,60 | 0,90 |
| Idioma | 1,00 | 1,00 | 1,00 |
| Correção dos snippets | 0,68 | 0,60 | 0,72 |

| Uso por turno | p50 | p95 |
| --- | --- | --- |
| Custo | US$ 0,0009 | US$ 0,0013 |
| Latência | 5,0 s | 7,5 s |

Taxa de acerto do cache no experimento: 35% dos tokens de entrada. Por conversa de vários turnos: 72% na de listas, 27% na de dicionários e 0% na de índice, a mais curta.

O que essa linha de base mostrou:

- **Perguntas recentes: correção zero em todas as cinco.** Inclui a sintaxe de genéricos do 3.12, anterior ao corte de treinamento do modelo: a resposta usou `def f[*T]`, que é outra coisa (`TypeVarTuple`). Nas três do 3.14, o modelo não conhece os recursos. É a lacuna que a ferramenta de consulta à documentação tem de fechar.
- **A régua da correção técnica está alta demais.** Exigir todos os pontos-chave reprova respostas boas por um detalhe: "lista vs tupla" falhou por não dizer que só tupla de itens imutáveis vira chave de dicionário, e "push" falhou por não citar o `AttributeError`. Uma nota só mistura dois defeitos diferentes: afirmar algo errado e deixar de cobrir um ponto.
- **Os snippets falham mais por `NameError` que por erro de verdade.** As respostas montam o exemplo em vários blocos (a lista é criada num e usada no seguinte), e cada bloco roda sozinho. A métrica mede hoje se o bloco roda isolado, não se o código está certo.
- **Os critérios didáticos quase não separam respostas.** Passo a passo, exemplos e idioma passaram em todos os turnos. Ou o tutor já cumpre, ou os critérios estão frouxos; só a calibração com rótulos humanos responde qual dos dois.
- **O cache funciona onde deve,** nas conversas que passam de 1.024 tokens, e a latência acompanha o tamanho da resposta: as de 9 s são as mais longas.

## Deixado de fora

- **Similaridade com uma resposta de referência (BLEU, ROUGE ou embeddings).** Mede o quanto a resposta se parece com um texto, não se ela está certa e ensina bem; numa resposta aberta, duas explicações corretas podem ter pouca sobreposição.
- **Tempo até o primeiro token.** A CLI ainda não usa streaming, então o aluno espera a resposta inteira, e a latência total é o que ele sente. A métrica entra junto com o streaming.
- **Custo do juiz.** O experimento mede o custo do chatbot, que é o que escala com os alunos. O do juiz é custo de desenvolvimento e aparece no LangSmith.
