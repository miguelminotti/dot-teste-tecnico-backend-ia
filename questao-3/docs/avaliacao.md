# Avaliação da questão 3

A busca é construída por desenvolvimento guiado por avaliação (*evaluation-driven development*, Chip Huyen, *AI Engineering*, 2025), como o chatbot da questão 2: as consultas de avaliação vêm antes do modelo de embeddings, e cada escolha (modelo, tamanho do pedaço, busca por termos, busca híbrida) entra se melhorar as métricas. O livro (cap. 6) pede exatamente isso para a recuperação: um conjunto de consultas de teste em que cada documento é anotado como relevante ou não, por pessoas ou por um juiz de IA.

## Conjunto de consultas

Fica em [`evals/queries.json`](../evals/queries.json), versionado com o código: 99 consultas, cada uma em inglês e em português, sobre o [corpus](corpus.md) de 100 artigos.

| Tipo | Consultas | O que testa | Artigos relevantes por consulta |
| --- | --- | --- | --- |
| `named` | 30 | a consulta usa o nome próprio do método, dataset ou benchmark ("AccentCL class-incremental accent classification"): nomes novos, que o livro aponta como o ponto fraco dos embeddings | 1 |
| `paraphrase` | 30 | a mesma ideia sem nenhum termo próprio do artigo ("how to keep adding new speech accent categories without retraining from scratch"): onde a busca por termos não tem palavra para casar | 1 a 7 (mediana 1) |
| `detail` | 29 | um detalhe que só um parágrafo do corpo responde, não o resumo ("what accent groups are in the dataset built for incremental English accent classification?") | 1 a 5 (mediana 1) |
| `topic` | 10 | um tema de pesquisa com vários artigos ("how can LLM agents learn reusable procedural guidance from their own trajectories?") | 3 a 18 |

**As duas línguas.** O corpus é em inglês. A versão em português mede a busca entre idiomas: quem pergunta em português e espera o artigo em inglês. Nesse caso a busca por termos não tem como casar, e só um modelo de embeddings multilíngue acerta. Os rótulos valem para as duas versões.

Cada consulta:

```json
{
  "id": "q006",
  "type": "detail",
  "query": {"en": "What accent groups are in the dataset built for incremental English accent classification?", "pt": "..."},
  "relevant": ["2610.07426"],
  "source": "2610.07426",
  "evidence": {"paper": "2610.07426", "section": "Datasets", "paragraph": 25, "quote": "The full dataset includes North American (NA), British Isles (BI), ..."},
  "needs_review": false,
  "judge_reasoning": "..."
}
```

**Relevância em dois níveis.** `relevant` lista os artigos relevantes, e é com ela que se mede a busca por artigo. Nas consultas de detalhe, `evidence` traz a frase do artigo que responde, copiada sem mudança (o script confere). É com ela que se mede a busca por trecho: um pedaço recuperado é relevante se contém a frase. O rótulo não depende de como o texto for dividido, e o mesmo conjunto serve para comparar tamanhos de pedaço.

## Como foi gerado

```bash
uv run --env-file .env semantic-search-queries
```

O código está em `src/semantic_search/evaluation/queries.py`.

1. **Trechos.** Sorteia 30 artigos (semente 7) e um parágrafo de pelo menos 60 palavras de cada um.
2. **Consultas por artigo.** O `gpt-5.4-mini` recebe o título, o resumo e o parágrafo e escreve as três consultas, nas duas línguas. Se a frase de evidência não for cópia do parágrafo, ele tenta de novo; na segunda falha, o artigo é pulado (não aconteceu).
3. **Consultas por tema.** O mesmo modelo lê os títulos e resumos dos 100 artigos e propõe 10 temas, cada um tratado por 2 a 8 artigos.
4. **Rótulos.** O `gpt-5.4`, mais forte que o gerador, lê os títulos e resumos dos 100 artigos para cada consulta, justifica e diz quais são relevantes. O artigo de origem é sempre relevante, porque a consulta foi escrita a partir dele. Quando o juiz discorda disso, a consulta é marcada para revisão.

Rotular o corpus inteiro, e não só o artigo de origem, é o que permite medir a cobertura (recall) da busca, como o livro aponta. Também evita punir a busca por acertos: em 10 das consultas por artigo, o juiz achou outros artigos relevantes além do de origem. A paráfrase "how to give step-level credit from teacher and student disagreement" tem 7 artigos relevantes, e não só o de origem.

## Revisão

Um piloto com 3 artigos mostrou dois problemas do prompt, corrigidos antes da rodada completa:

- **Português com inglês demais** ("O que causa false alarms nas checks de um validation harness"). A busca por termos casaria pelas palavras em inglês, e a medida entre idiomas ficaria inflada. O prompt passou a pedir tradução de toda palavra comum, deixando em inglês só nomes próprios e os termos que a área não traduz (LLM, fine-tuning, embedding, benchmark, prompt, token).
- **Consulta pelo nome como lista de palavras-chave** ("SpecGuardBench validation harness benchmark coding agents"). Isso favorece a busca por termos. O prompt passou a pedir pergunta ou frase natural.

Na rodada completa, cada consulta foi lida. As alteradas guardam o texto original, os rótulos de antes e o motivo, no campo `revision`. As reescritas foram rotuladas de novo pelo juiz.

- **8 consultas de detalhe que não se sustentavam sozinhas:** falavam de "o dataset construído", "o primeiro experimento", "a votação ponderada". Nenhum buscador saberia de qual artigo se trata, então foram reescritas com o assunto na pergunta.
- **2 consultas pelo nome com nome inválido:**
  - "circleclar" é a macro do LaTeX que o resumo do arXiv traz sem expandir;
  - "A Jury" é um pedaço do título, e não nome de método.

  Foram reescritas com o termo mais específico do artigo.
- **1 correção só no português:** "Quais benchmark".
- **1 consulta removida (`q036`).** O trecho dela era uma lista de trabalhos de outros autores, da seção de trabalhos relacionados, e o artigo de origem não trata do que a pergunta pedia. Reescrita, ela ficou genérica, e o juiz a ligou a artigos que só tinham "explicação" em comum.
- **1 consulta marcada pelo juiz e mantida (`q021`).** O detalhe (o protocolo SPoRC) está no corpo do artigo, e o juiz lê só os resumos.

## Métricas

```bash
uv run semantic-search-eval
uv run semantic-search-eval --model intfloat/multilingual-e5-base --method hybrid
```

O código está em `src/semantic_search/evaluation/metrics.py` e `retrieval.py`. Cada consulta roda nas duas línguas, num total de 198 buscas. As médias saem por tipo de consulta e por língua, porque cada tipo testa uma fraqueza diferente. A tabela vai para o terminal, e as notas e os 10 primeiros artigos de cada busca vão para `evals/results/<método>__<modelo>.json`, para a análise dos erros. A opção `--method` escolhe a busca: só embeddings (`dense`, o padrão), só termos (`bm25`) ou as duas (`hybrid`). Os resultados estão em [`experimentos.md`](experimentos.md).

**Por artigo,** nos 10 primeiros resultados da [função de busca](busca.md), contra os artigos rotulados pelo juiz:

| Métrica | O que mede |
| --- | --- |
| Recall@10 | a fração dos artigos relevantes que aparece entre os 10 primeiros: a cobertura |
| P@10 | a fração dos 10 primeiros que é relevante. Em 79 das 99 consultas há um relevante só, e o máximo é 0,1: a métrica fica registrada, mas não decide nada |
| MRR | 1 sobre a posição do primeiro relevante, ou 0 se ele não está entre os 10: o quanto o leitor precisa descer |
| NDCG@10 | a ordem dos relevantes, com desconto pela posição, dividida pela da ordem ideal. Com mais relevantes que 10, a ordem ideal enche os 10 primeiros, e a busca perfeita tira 1 |
| R-precision | a precisão nas R primeiras posições, sendo R o número de relevantes. Três temas têm de 14 a 18 relevantes, e a cobertura em 10 não chega a 1 nem com a busca perfeita; a R-precision chega |

**Por trecho,** só nas 29 consultas de detalhe, sobre os 10 pedaços mais parecidos com a consulta, sem agrupar por artigo. O pedaço relevante é o que contém a citação de evidência, com o espaço entre as palavras normalizado, como na geração. Cada uma das 29 citações está em exatamente um dos 5.398 pedaços, no parágrafo certo (conferido).

| Métrica | O que mede |
| --- | --- |
| Trecho@10 | a fração das consultas em que o pedaço que responde está entre os 10 mais parecidos |
| MRR trecho | 1 sobre a posição desse pedaço entre os 10, ou 0 |

As médias foram conferidas por outro caminho: numpy puro, com o máximo por artigo sobre todos os pedaços, sem o FAISS e sem as funções de métrica. Os 10 primeiros artigos das 198 buscas e todas as médias saíram iguais.

## Limitações

- **O juiz lê resumos, não o texto inteiro.** Um artigo que trata do assunto só no corpo pode ficar de fora dos relevantes, sobretudo nas consultas de detalhe. Ler os 100 artigos inteiros por consulta custaria cerca de 600 mil tokens de entrada cada.
- **Consultas escritas a partir do texto tendem a repetir as palavras dele.** Isso favorece a busca por termos nas consultas pelo nome e de detalhe. As paráfrases e a versão em português existem para equilibrar isso.
- **Os rótulos não foram calibrados com rótulos humanos.** A revisão leu as consultas e conferiu os casos marcados, mas não rotulou a relevância de cada artigo para comparar com o juiz.
- **Temas largos têm mais relevantes do que cabem no topo.** Três temas têm 14 a 18 artigos relevantes, e a cobertura nos 10 primeiros resultados não chega a 1 nem com a busca perfeita. As métricas precisam levar isso em conta.
