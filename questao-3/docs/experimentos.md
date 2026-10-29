# Experimentos

Cada mudança na busca é medida nas [consultas de avaliação](avaliacao.md), com as métricas descritas lá, e entra se melhorar os números. Os resultados por consulta de cada rodada ficam em `evals/results/`.

## Linha de base: embeddings do `multilingual-e5-base`

Um pedaço por parágrafo, mais um com título e resumo por artigo ([`indexacao.md`](indexacao.md)), busca exata no FAISS e cada artigo pela nota do melhor pedaço ([`busca.md`](busca.md)).

| Tipo | Língua | Consultas | Recall@10 | P@10 | MRR | NDCG@10 | R-prec. | Trecho@10 | MRR trecho |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| named | en | 30 | 1.000 | 0.100 | 0.970 | 0.976 | 0.967 |  |  |
| named | pt | 30 | 1.000 | 0.100 | 0.978 | 0.983 | 0.967 |  |  |
| named | ambas | 60 | 1.000 | 0.100 | 0.974 | 0.980 | 0.967 |  |  |
| paraphrase | en | 30 | 0.950 | 0.140 | 0.900 | 0.890 | 0.775 |  |  |
| paraphrase | pt | 30 | 0.940 | 0.133 | 0.799 | 0.800 | 0.618 |  |  |
| paraphrase | ambas | 60 | 0.945 | 0.137 | 0.849 | 0.845 | 0.697 |  |  |
| detail | en | 29 | 0.986 | 0.110 | 0.983 | 0.973 | 0.934 | 0.828 | 0.543 |
| detail | pt | 29 | 0.986 | 0.110 | 0.943 | 0.938 | 0.859 | 0.724 | 0.487 |
| detail | ambas | 58 | 0.986 | 0.110 | 0.963 | 0.955 | 0.897 | 0.776 | 0.515 |
| topic | en | 10 | 0.489 | 0.360 | 0.900 | 0.566 | 0.419 |  |  |
| topic | pt | 10 | 0.484 | 0.350 | 0.800 | 0.523 | 0.360 |  |  |
| topic | ambas | 20 | 0.486 | 0.355 | 0.850 | 0.545 | 0.389 |  |  |
| todos | en | 99 | 0.929 | 0.141 | 0.945 | 0.908 | 0.844 | 0.828 | 0.543 |
| todos | pt | 99 | 0.926 | 0.138 | 0.895 | 0.868 | 0.768 | 0.724 | 0.487 |
| todos | ambas | 198 | 0.927 | 0.140 | 0.920 | 0.888 | 0.806 | 0.776 | 0.515 |

### O que os números dizem

- **Nomes novos não foram o ponto fraco esperado.** O livro aponta os termos que o modelo nunca viu como a fraqueza dos embeddings, mas as consultas pelo nome acertam o artigo entre os 10 primeiros em todas as 60 buscas, com MRR de 0,974. O nome costuma estar no título e no resumo, que formam um pedaço, e a consulta repete outras palavras do artigo, uma limitação conhecida do conjunto. A exceção é a q067 ("Rogan–Gladen correction for interactive LLM evaluation"): o artigo certo fica em 10º em inglês e em 3º em português. Rogan–Gladen é uma correção estatística citada no corpo do artigo, um termo raro que a busca por termos casaria pela palavra exata.
- **A consulta em português perde para a mesma consulta em inglês.** O MRR é menor em português em 14 consultas e maior em 5. A diferença aparece nas paráfrases (MRR de 0,900 para 0,799, R-precision de 0,775 para 0,618), e não nos nomes, que são iguais nas duas línguas. Um artigo sozinho explica boa parte: o do Manacá (2610.20570), sobre um LLM em português brasileiro, fica em 1º, no lugar do certo, em 7 buscas em português por artigo, e em 10 contando os temas. O embedding casa a língua da consulta com o assunto "português". A busca por termos não resolve esse caso, porque a consulta em português não tem palavras em comum com o artigo em inglês.
- **Na consulta de detalhe, o artigo certo vem, mas o parágrafo que responde nem sempre.** Os 10 primeiros trazem 98,6% dos artigos relevantes, e o primeiro relevante costuma vir em 1º (MRR de 0,963). Já o pedaço que contém a resposta está entre os 10 pedaços mais parecidos em só 77,6% das buscas, e longe do topo (MRR de 0,515). Para um RAG, é o trecho que vai para o modelo, não o artigo.
- **Temas são o pior caso em cobertura.** Recall@10 de 0,486 e R-precision de 0,389: metade dos relevantes fica fora dos 10 primeiros. O primeiro resultado costuma ser relevante (MRR de 0,850). Aqui a medida é a mais frágil: o juiz leu só os resumos, os temas são largos (a q095 tem 18 relevantes), e a fronteira do que é relevante é mais subjetiva.

### Próximos experimentos, na ordem que os números sugerem

1. **BM25 e busca híbrida com RRF.** Ataca os termos raros (q067) e pode trazer o parágrafo exato nas consultas de detalhe, que repetem palavras do texto. Não deve ajudar o português. Feito: [abaixo](#bm25-e-busca-híbrida).
2. **Prefixo de contexto no pedaço (título e seção), o *contextual retrieval* do livro.** Um parágrafo solto ("we use the full dataset") não diz de que artigo é, e o prefixo pode levar os pedaços certos ao topo nos detalhes e nos temas.
3. **Outros modelos (`BAAI/bge-m3`, `Qwen/Qwen3-Embedding-0.6B`).** É onde o viés de língua pode mudar, e a GPU torna o teste barato (o e5-base levou 48 s). Feito só com o bge-m3: [abaixo](#outro-modelo-bge-m3).
4. **Tamanho do pedaço.** O rótulo por trecho é a frase de evidência, e não o pedaço, e serve para qualquer divisão em que as frases caibam inteiras: com pedaços de 100 palavras, três delas ficariam divididas, e a avaliação recusa o índice ([avaliação](avaliacao.md)).

## BM25 e busca híbrida

O código está em `src/semantic_search/retrievers.py`. A busca e a avaliação recebem `--method dense|bm25|hybrid`.

```bash
uv run semantic-search-eval --method hybrid
```

- **BM25 pelo `bm25s`,** sobre os mesmos pedaços. A biblioteca está em manutenção e depende só do numpy. O `rank-bm25` está parado desde 2022. Parâmetros padrão (k1 = 1,5, b = 0,75). As palavras passam para minúsculas, perdem as stopwords e são reduzidas ao radical com o stemmer Snowball do inglês.
- **As stopwords são as do inglês e as do português.** Na primeira rodada, só com as do inglês, toda consulta em português casava por "de", "em" e "que", que existem no corpus ("de Vries", o texto em português do artigo do Manacá). Com as duas listas, o MRR da híbrida em português subiu de 0,679 para 0,778, medido antes da [correção dos itens de lista](corpus.md#correção-dos-itens-de-lista) do corpus. O custo: as siglas "EM" (*exact match*) e "SER" (*speech emotion recognition*), com cerca de 20 ocorrências cada no corpus, viram "em" e "ser" e deixam de casar. Nenhuma consulta de avaliação usa essas siglas.
- **O BM25 devolve só os pedaços com algum termo da consulta.** O `bm25s` devolve também os de nota 0, em ordem arbitrária, que na híbrida virariam ruído.
- **A híbrida funde as duas listas pelo RRF, com k = 60,** a constante do artigo original (Cormack et al., 2009) e a que o livro cita. Cada pedaço soma 1 / (60 + posição) em cada lista. O RRF usa só as posições, porque as notas não se comparam (cosseno de um lado, BM25 do outro). A fusão é sobre as listas completas, e não cortadas em *n*: com o corte, um pedaço em (n+1)º nas duas listas ficaria de fora, valendo mais que um que só uma delas pôs em 1º. Com 5 mil pedaços, a lista completa custa poucos milissegundos.

### Resultados

Todas as consultas, por língua:

| Busca | Língua | Recall@10 | MRR | NDCG@10 | R-prec. | Trecho@10 | MRR trecho |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Embeddings | en | 0.929 | 0.945 | 0.908 | 0.844 | 0.828 | 0.543 |
| BM25 | en | 0.942 | 0.960 | 0.926 | 0.866 | 0.966 | 0.605 |
| Híbrida (RRF) | en | 0.935 | 0.990 | 0.935 | 0.894 | 0.897 | 0.595 |
| Embeddings | pt | 0.926 | 0.895 | 0.868 | 0.768 | 0.724 | 0.487 |
| BM25 | pt | 0.610 | 0.493 | 0.506 | 0.415 | 0.448 | 0.220 |
| Híbrida (RRF) | pt | 0.898 | 0.794 | 0.779 | 0.632 | 0.690 | 0.397 |
| Embeddings | ambas | 0.927 | 0.920 | 0.888 | 0.806 | 0.776 | 0.515 |
| BM25 | ambas | 0.776 | 0.727 | 0.716 | 0.640 | 0.707 | 0.413 |
| Híbrida (RRF) | ambas | 0.916 | 0.892 | 0.857 | 0.763 | 0.793 | 0.496 |

MRR por tipo de consulta:

| Tipo | Embeddings en | BM25 en | Híbrida en | Embeddings pt | BM25 pt | Híbrida pt |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| named | 0.970 | 1.000 | 1.000 | 0.978 | 0.770 | 0.889 |
| paraphrase | 0.900 | 0.919 | 0.983 | 0.799 | 0.178 | 0.690 |
| detail | 0.983 | 0.966 | 0.983 | 0.943 | 0.579 | 0.805 |
| topic | 0.900 | 0.950 | 1.000 | 0.800 | 0.358 | 0.783 |

As tabelas completas, por tipo e língua, estão nos arquivos `evals/results/<método>__intfloat__multilingual-e5-base.json`.

### O que os números dizem

- **Em inglês, a híbrida é a melhor busca em quase tudo.** O MRR vai de 0,945 (embeddings) para 0,990, e a R-precision de 0,844 para 0,894. As paráfrases, onde a busca por termos não tem palavra para casar, sobem de 0,900 para 0,983: as duas listas erram em consultas diferentes, e a fusão acerta as duas. A q067 ("Rogan–Gladen"), que os embeddings punham em 10º, vai para 1º.
- **O BM25 sozinho, em inglês, já empata ou passa os embeddings.** O MRR é 0,960 e o Trecho@10, 0,966: o parágrafo que responde ao detalhe vem entre os 10 primeiros pedaços em quase todas as buscas. Parte disso é a limitação conhecida do conjunto: as consultas foram escritas a partir do texto e repetem as palavras dele. O número mede um caso favorável ao BM25, não o uso real.
- **Em português, a híbrida perde para os embeddings sozinhos.** O MRR cai de 0,895 para 0,794. O BM25 em português só casa nomes próprios e palavras iguais nas duas línguas ("LLM", "benchmark"), e no resto traz ruído, que o RRF mistura à lista boa dos embeddings. O ímã do Manacá piora: o artigo fica em 1º, no lugar do certo, em 11 buscas em português, contra 10 só com embeddings, porque o texto dele tem palavras em português ("comecar_com", "min_maiusculas").
- **No total, os embeddings sozinhos ainda vencem no artigo, e a híbrida vence no trecho.** O MRR das 198 buscas é 0,920 com embeddings e 0,892 com a híbrida. O Trecho@10 é 0,776 com embeddings e 0,793 com a híbrida.

### Decisão

A busca continua só com embeddings por padrão (`--method dense`). A híbrida melhora o inglês e piora o português, e metade das consultas é em português. Os dois caminhos que os números sugerem:

- **Escolher a busca pela língua da consulta:** a híbrida em inglês e os embeddings em português. Com a língua conhecida, como no conjunto de avaliação, as médias das 198 buscas seriam 0,943 de MRR, 0,831 de R-precision e 0,810 de Trecho@10, acima das duas buscas sozinhas. Na prática, isso exige detectar a língua de consultas curtas e feitas quase só de nomes, como "ARMOR-DP para Multilingual BabyLM", em que só "para" é português.
- **Traduzir a consulta para o inglês antes do BM25:** daria ao BM25 em português as mesmas palavras que ele casa em inglês, ao custo de uma chamada a um modelo de tradução por consulta.

## Outro modelo: bge-m3

O `BAAI/bge-m3` é multilíngue, tem licença MIT, 568 milhões de parâmetros (o dobro do e5-base) e vetores de 1.024 dimensões, e não usa prefixo de consulta nem de documento. Os pedaços são os mesmos do e5 (o `chunks.jsonl` sai idêntico), e a diferença mede só o modelo.

```bash
uv run --no-sync semantic-search-embed --model BAAI/bge-m3
uv run --no-sync semantic-search-store --model BAAI/bge-m3
uv run --no-sync semantic-search-eval --model BAAI/bge-m3 --method dense
```

Ficou só o bge-m3, e não o Qwen3-Embedding-0.6B. A pergunta era se outro modelo resolve o viés de língua, e um modelo responde. Com 99 consultas, comparar muitos modelos e variantes tenderia a escolher o que se ajusta a este conjunto.

### Resultados

| Modelo | Busca | Língua | Recall@10 | MRR | NDCG@10 | R-prec. | Trecho@10 | MRR trecho |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| e5-base | Embeddings | en | 0.929 | 0.945 | 0.908 | 0.844 | 0.828 | 0.543 |
| bge-m3 | Embeddings | en | 0.942 | 0.948 | 0.914 | 0.836 | 0.828 | 0.568 |
| e5-base | Híbrida | en | 0.935 | 0.990 | 0.935 | 0.894 | 0.897 | 0.595 |
| bge-m3 | Híbrida | en | 0.935 | 0.985 | 0.935 | 0.879 | 0.931 | 0.630 |
| e5-base | Embeddings | pt | 0.926 | 0.895 | 0.868 | 0.768 | 0.724 | 0.487 |
| bge-m3 | Embeddings | pt | 0.931 | 0.939 | 0.899 | 0.814 | 0.793 | 0.515 |
| e5-base | Híbrida | pt | 0.898 | 0.794 | 0.779 | 0.632 | 0.690 | 0.397 |
| bge-m3 | Híbrida | pt | 0.918 | 0.840 | 0.820 | 0.694 | 0.690 | 0.399 |
| e5-base | Embeddings | ambas | 0.927 | 0.920 | 0.888 | 0.806 | 0.776 | 0.515 |
| bge-m3 | Embeddings | ambas | 0.937 | 0.943 | 0.906 | 0.825 | 0.810 | 0.541 |
| e5-base | Híbrida | ambas | 0.916 | 0.892 | 0.857 | 0.763 | 0.793 | 0.496 |
| bge-m3 | Híbrida | ambas | 0.926 | 0.912 | 0.877 | 0.786 | 0.810 | 0.515 |

MRR por tipo de consulta, só embeddings:

| Tipo | e5-base en | bge-m3 en | e5-base pt | bge-m3 pt |
| --- | ---: | ---: | ---: | ---: |
| named | 0.970 | 1.000 | 0.978 | 1.000 |
| paraphrase | 0.900 | 0.903 | 0.799 | 0.899 |
| detail | 0.983 | 0.957 | 0.943 | 0.931 |
| topic | 0.900 | 0.900 | 0.800 | 0.900 |

| Custo | e5-base | bge-m3 |
| --- | ---: | ---: |
| Embeddings do corpus na GPU (RTX 3060) | 48 s | 152 s |
| Embeddings do corpus na CPU (i7-4790K, estimado por uma amostra de 200 pedaços) | cerca de 22 min | cerca de 85 min |
| Embedding de uma consulta na GPU (mediana) | 12,5 ms | 23,2 ms |
| Download do modelo (cache da Hugging Face) | 1,1 GB | 4,3 GB: o repositório traz os pesos em dois formatos, de 2,3 GB cada, e os dois foram baixados |
| Índice FAISS | 15,5 MB | 20,6 MB |

### O que os números dizem

- **O bge-m3 desfaz o ímã do português.** Com o e5, o artigo do Manacá ficava em 1º, no lugar do certo, em 10 buscas em português; com o bge-m3, em 1. As consultas em que o português perde para o inglês caem de 14 para 4. Uma queda de 10 para 1 casos de um erro sistemático não é acaso. A q067 ("Rogan–Gladen"), que o e5 punha em 10º, vem em 1º nas duas línguas, só com embeddings.
- **Nas médias, a diferença está dentro do ruído do conjunto.** Num bootstrap pareado, sorteando as 99 consultas 10 mil vezes, a diferença de MRR (bge-m3 − e5) é de +0,044 em português, com intervalo de 95% de [−0,006; +0,095], e de +0,003 em inglês, com intervalo de [−0,031; +0,039]. No total, o MRR vai de 0,920 para 0,943, e a R-precision de 0,806 para 0,825, com intervalo de [−0,030; +0,067] para a diferença. O conjunto não tem tamanho para separar dois modelos bons por diferenças desse tamanho.
- **A híbrida continua pior que os embeddings sozinhos em português,** também com o bge-m3: MRR de 0,840 contra 0,939. O problema é o BM25 em português, e não o modelo.
- **O custo é o dobro na consulta e quase o quádruplo na indexação.** Na GPU isso é pouco (23 ms por consulta, menos de 3 minutos para o corpus). Sem GPU, a indexação passa de cerca de 22 para cerca de 85 minutos nesta máquina.

### Decisão

O bge-m3 passa a ser o modelo padrão, e o e5-base fica como a opção leve para quem indexa sem GPU ([ADR 0001](adr/0001-modelo-de-embeddings-bge-m3.md)). As médias não separam os dois, mas o erro que o bge-m3 elimina é sistemático e fica à vista de quem busca em português. A busca padrão continua só com embeddings.
