# Avaliação da questão 2

O chatbot foi construído guiado por avaliação (Chip Huyen, *AI Engineering*, 2025): o dataset e as métricas vieram antes da arquitetura, e cada peça (modelo, regra do prompt, busca na documentação) só entrou se melhorou uma métrica sem estourar as outras. Os experimentos rodam no LangSmith; o código está em `src/chatbot/evaluation/`.

## Como rodar

Com `OPENAI_API_KEY` e `LANGSMITH_API_KEY` no `.env` e o Python 3.14 instalado (`uv python install 3.14`), na pasta da questão. Os braços de uma comparação mudam só as variáveis do chatbot; o experimento da busca rodou assim:

```bash
CHATBOT_MODEL=gpt-4.1-mini CHATBOT_DOCS_SEARCH=false uv run --env-file .env chatbot-eval
CHATBOT_MODEL=gpt-5.4-mini CHATBOT_DOCS_SEARCH=false uv run --env-file .env chatbot-eval
CHATBOT_MODEL=gpt-5.4-mini CHATBOT_DOCS_SEARCH=true uv run --env-file .env chatbot-eval
```

## Dataset

Fica em [`evals/dataset.json`](../evals/dataset.json), versionado junto com o código, para que uma mudança nele passe por revisão no diff. No LangSmith, o nome do dataset leva o hash do arquivo: mudar o arquivo cria um dataset novo, e cada experimento fica ligado à versão em que rodou. Os experimentos abaixo rodaram em `dot-questao-2-a70fadc0` (hash com o CRLF do checkout no Windows; com o final de linha normalizado, o mesmo conteúdo vira `dot-questao-2-352e255e`).

São 15 **conversas**, cada turno com a pergunta e os **pontos-chave** que a resposta precisa cobrir. Pontos-chave no lugar de uma resposta de referência porque uma pergunta de programação tem muitas respostas certas. As categorias são `basico` (inclui o exemplo do enunciado), `armadilha`, `premissa-falsa`, `intermediario`, `recente`, `biblioteca`, `fora-do-escopo` e `conversa` (vários turnos que dependem do histórico). Cada conversa tem ainda `released_on`, a data do recurso, que separa o que o modelo não tem como saber, e `python_version`, a versão em que os snippets da resposta rodam.

## Métricas

| Métrica | Como mede |
| --- | --- |
| Precisão factual (juiz) | fração dos turnos sem nada tecnicamente errado ou enganoso, inclusive no código; omissão não conta |
| Cobertura dos pontos-chave (juiz) | fração dos pontos-chave que a resposta transmite, contada por ponto |
| Qualidade didática (juiz) | responde à pergunta, passo a passo, exemplos, nível de detalhe e idioma, cada um com veredito próprio |
| Correção dos snippets | fração dos blocos ` ```python ` que rodam sem erro na `python_version` da conversa |
| Uso da busca | fração dos turnos com ao menos uma busca na documentação |
| Custo e latência do turno | US$ por mil turnos (tokens vezes a tabela de `usage.py`, mais US$ 0,01 por busca) e segundos, em p50 e p95 |

O juiz (`gpt-5.4`, configurável em `EVAL_JUDGE_MODEL`) dá passa ou falha por critério, com a justificativa antes do veredito, numa chamada por turno, vendo a conversa até ali. Nota de 1 a 10 ficou de fora porque oscila entre execuções e não diz o que melhorar. Erro e omissão são separados: na primeira linha de base, uma nota só ("cobre todos os pontos e não erra") reprovou 78% das respostas, muitas delas certas e incompletas. O juiz ainda não foi calibrado contra rótulos humanos, e não conhece o Python 3.14: nas perguntas recentes, ele só é confiável no que está nos pontos-chave, e o resto quem confere é a execução dos snippets.

Os snippets rodam num processo restrito: Python fora do ambiente virtual, modo isolado (`-I`), diretório temporário, tempo limite de 10 s e sem as chaves no ambiente. Restrito não é isolado (o processo ainda lê o disco e acessa a rede); o risco é baixo porque as perguntas são do dataset e as páginas da busca são de domínios oficiais. Os blocos de uma resposta rodam em sequência, como o aluno que acompanha a explicação, e um bloco que falhou fica de fora dos seguintes. Snippet que importa pacote fora da biblioteca padrão é pulado, sem contar como falha.

### Cache de prompt

Com histórico, cada turno reenvia a conversa inteira. O cache de prompt da OpenAI cobra mais barato a parte inicial da entrada idêntica à de uma chamada recente, por isso o prompt de sistema vem primeiro e o histórico só cresce no fim. A avaliação mede a taxa de acerto (tokens lidos do cache sobre o total de entrada), mas ela não se compara entre os braços: abaixo de cerca de 1.024 tokens nada é cacheado, e as conversas do dataset ficam perto desse mínimo.

## Resultados

A escolha que estes resultados sustentam, o `gpt-5.4-mini` com busca, está na [ADR 0002](adr/0002-busca-na-documentacao-com-gpt-5-4-mini.md). Os valores são a média, entre as conversas, da nota de cada uma. "Recentes" são as categorias `recente` e `biblioteca` (5 conversas); "demais" são as outras 10. Cada experimento rodou uma vez, e nas recentes cada conversa vale 0,20 da média: diferenças pequenas podem ser só variação entre execuções.

### Busca na documentação: três braços (2026-10-28)

A busca hospedada da OpenAI só existe na Responses API, e o `gpt-4.1-mini` recusa o filtro que a restringe aos domínios oficiais. Por isso três braços: o `gpt-4.1-mini` sem busca é a linha de base; o `gpt-5.4-mini` sem busca mede a troca de modelo; o `gpt-5.4-mini` com busca mede a busca. Sem o braço do meio, o ganho do modelo novo seria atribuído à busca. Experimentos `gpt-4.1-mini-6dbe9b20`, `gpt-5.4-mini-33439684` e `gpt-5.4-mini-busca-0e1e2950`, sem erro em nenhuma conversa.

| Métrica | 4.1-mini | 5.4-mini | 5.4-mini com busca |
| --- | --- | --- | --- |
| Precisão factual, recentes | 0,00 | 0,20 | **0,60** |
| Cobertura, recentes | 0,30 | 0,50 | 0,65 |
| Precisão factual, demais | 1,00 | 1,00 | 1,00 |
| Cobertura, demais | **0,82** | 0,74 | 0,77 |
| Correção dos snippets, demais | 0,97 | 0,88 | 0,93 |
| Turnos com busca, recentes / demais | – | – | 2 de 5 / 0 de 18 |
| Custo p50 (US$ por mil turnos) | 0,90 | 2,49 | 3,11 |
| Custo p95 | 1,61 | 4,72 | 17,37 |
| Latência p50 | 4,5 s | 2,7 s | 2,2 s |

- **A busca é o que corrige as perguntas recentes.** O modelo novo sozinho acerta o que é anterior ao corte de treinamento dele (genéricos do 3.12, `model_dump()` do Pydantic v2); as t-strings e o `compression.zstd` do 3.14 só saem certos com a busca, e com a página citada.
- **O modelo busca só quando sabe que não sabe.** Buscou nas perguntas que citam o 3.14 e em nenhuma das 18 do resto. Mas em "posso escrever `except ValueError, TypeError:`?", que não cita versão, respondeu "não" com confiança, sem buscar, e errou: o 3.14 passou a aceitar (PEP 758).
- **A busca pesa na cauda do custo, não no típico.** Um turno com busca custa cerca de US$ 0,018, uns 7 vezes o turno sem busca; com a busca só onde precisa, o p50 sobe 25% e o p95 quase quadruplica.
- **Trocar de modelo encarece e encurta as respostas.** O `gpt-5.4-mini` custa cerca de 2,8 vezes o `gpt-4.1-mini` no p50 e oferece o resto ("Se quiser, posso mostrar...") em vez de explicar: no exemplo do enunciado, a cobertura cai de 1,00 para 0,50. A queda nos snippets é de formato: ele punha a saída do programa num bloco ` ```python `.

### Prompt ajustado pelas falhas dos três braços (2026-10-28)

Três regras entraram no prompt, cada uma por uma falha medida acima: explicar o essencial na própria resposta, pôr a saída do programa em blocos ` ```text ` e, com a busca ligada, buscar também quando a pergunta é se uma sintaxe existe (o caso do `except`). Rodaram de novo os dois braços do `gpt-5.4-mini` (`gpt-5.4-mini-eaac41d6` e `gpt-5.4-mini-busca-599186b5`). Entre parênteses, o valor anterior.

| Métrica | 5.4-mini | 5.4-mini com busca |
| --- | --- | --- |
| Precisão factual, recentes | 0,40 (0,20) | **0,80** (0,60) |
| Cobertura, recentes | 0,39 (0,50) | 0,61 (0,65) |
| Precisão factual, demais | 1,00 (1,00) | 0,97 (1,00) |
| Cobertura, demais | 0,82 (0,74) | 0,79 (0,77) |
| Correção dos snippets, geral | 0,87 (0,76) | **0,94** (0,84) |
| Turnos com busca, recentes | – | 3 de 5 (2 de 5) |
| Custo p50 (US$ por mil turnos) | 3,06 (2,49) | 3,06 (3,11) |
| Custo p95 | 5,02 (4,72) | 18,27 (17,37) |

- **O bloco de saída resolveu os snippets,** que passaram do `gpt-4.1-mini` (0,91 no geral).
- **O essencial na resposta encarece e ajuda pouco.** O custo p50 sem busca subiu 23%; o exemplo do enunciado deu 1,00 num braço e 0,50 no outro, com o mesmo prompt.
- **A regra não fez o modelo buscar no `except`.** Uma regra de prompt não resolve o caso em que o modelo não sabe que não sabe. Fechar esse caso pede dizer ao modelo qual é a versão atual do Python, ou buscar em todo turno (cerca de US$ 20 por mil turnos).
- **A única falha de precisão no resto é de fronteira:** o juiz reprovou `if indice < len(numeros):` para evitar o `IndexError`, porque um índice negativo inválido passa pelo `if`. A crítica procede.

### Linhas de base com o `gpt-4.1-mini` (2026-10-28)

Rodaram antes dos três braços, ainda fora da Responses API, e ficam como registro de por que as réguas mudaram. Na primeira (`gpt-4.1-mini-139b9a27`), a correção técnica era uma nota só e cada snippet rodava sozinho: a nota deu 0,22, e a maior parte das falhas de snippet era `NameError` de código certo que continuava o bloco anterior. Com as réguas atuais (`gpt-4.1-mini-4e2c001d`), a precisão foi 0,00 nas recentes e 0,90 no resto: o modelo recomendava o `.dict()` do Pydantic v1 e escrevia `repeat[int](5, 3)`, que dá `TypeError`, nos genéricos do 3.12.

## Deixado de fora

- **Similaridade com uma resposta de referência (BLEU, ROUGE, embeddings):** mede o quanto a resposta se parece com um texto, não se está certa.
- **Tempo até o primeiro token:** a CLI não usa streaming, então a latência total é o que o aluno sente.
- **Custo do juiz:** é custo de desenvolvimento e aparece no LangSmith; o experimento mede o do chatbot, que escala com os alunos.
