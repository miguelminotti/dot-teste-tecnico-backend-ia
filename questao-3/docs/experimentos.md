# Experimentos

Cada mudança na busca é medida nas [consultas de avaliação](avaliacao.md), com as métricas descritas lá, e entra se melhorar os números. Os resultados por consulta de cada rodada ficam em `evals/results/`.

## Linha de base: embeddings do `multilingual-e5-base`

Um pedaço por parágrafo, mais um com título e resumo por artigo ([`indexacao.md`](indexacao.md)), busca exata no FAISS e cada artigo pela nota do melhor pedaço ([`busca.md`](busca.md)).

| Tipo | Língua | Consultas | Recall@10 | P@10 | MRR | NDCG@10 | R-prec. | Trecho@10 | MRR trecho |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| named | en | 30 | 1.000 | 0.100 | 0.970 | 0.976 | 0.967 |  |  |
| named | pt | 30 | 1.000 | 0.100 | 0.978 | 0.983 | 0.967 |  |  |
| named | ambas | 60 | 1.000 | 0.100 | 0.974 | 0.980 | 0.967 |  |  |
| paraphrase | en | 30 | 0.950 | 0.140 | 0.900 | 0.888 | 0.780 |  |  |
| paraphrase | pt | 30 | 0.951 | 0.137 | 0.799 | 0.807 | 0.618 |  |  |
| paraphrase | ambas | 60 | 0.950 | 0.138 | 0.850 | 0.847 | 0.699 |  |  |
| detail | en | 29 | 0.986 | 0.110 | 0.983 | 0.972 | 0.934 | 0.828 | 0.536 |
| detail | pt | 29 | 0.986 | 0.110 | 0.943 | 0.938 | 0.859 | 0.724 | 0.481 |
| detail | ambas | 58 | 0.986 | 0.110 | 0.963 | 0.955 | 0.897 | 0.776 | 0.509 |
| topic | en | 10 | 0.489 | 0.360 | 0.900 | 0.566 | 0.412 |  |  |
| topic | pt | 10 | 0.477 | 0.340 | 0.800 | 0.510 | 0.349 |  |  |
| topic | ambas | 20 | 0.483 | 0.350 | 0.850 | 0.538 | 0.380 |  |  |
| todos | en | 99 | 0.929 | 0.141 | 0.945 | 0.907 | 0.845 | 0.828 | 0.536 |
| todos | pt | 99 | 0.928 | 0.138 | 0.895 | 0.869 | 0.767 | 0.724 | 0.481 |
| todos | ambas | 198 | 0.929 | 0.140 | 0.920 | 0.888 | 0.806 | 0.776 | 0.509 |

### O que os números dizem

- **Nomes novos não foram o ponto fraco esperado.** O livro aponta os termos que o modelo nunca viu como a fraqueza dos embeddings, mas as consultas pelo nome acertam o artigo entre os 10 primeiros em todas as 60 buscas, com MRR de 0,974. O nome costuma estar no título e no resumo, que formam um pedaço, e a consulta repete outras palavras do artigo, uma limitação conhecida do conjunto. A exceção é a q067 ("Rogan–Gladen correction for interactive LLM evaluation"): o artigo certo fica em 10º em inglês e em 3º em português. Rogan–Gladen é uma correção estatística citada no corpo do artigo, um termo raro que a busca por termos casaria pela palavra exata.
- **A consulta em português perde para a mesma consulta em inglês.** O MRR é menor em português em 14 consultas e maior em 5. A diferença aparece nas paráfrases (MRR de 0,900 para 0,799, R-precision de 0,780 para 0,618), e não nos nomes, que são iguais nas duas línguas. Um artigo sozinho explica boa parte: o do Manacá (2610.20570), sobre um LLM em português brasileiro, fica em 1º, no lugar do certo, em 7 buscas em português. O embedding casa a língua da consulta com o assunto "português". A busca por termos não resolve esse caso, porque a consulta em português não tem palavras em comum com o artigo em inglês.
- **Na consulta de detalhe, o artigo certo vem, mas o parágrafo que responde nem sempre.** Os 10 primeiros trazem 98,6% dos artigos relevantes, e o primeiro relevante costuma vir em 1º (MRR de 0,963). Já o pedaço que contém a resposta está entre os 10 pedaços mais parecidos em só 77,6% das buscas, e longe do topo (MRR de 0,509). Para um RAG, é o trecho que vai para o modelo, não o artigo.
- **Temas são o pior caso em cobertura.** Recall@10 de 0,483 e R-precision de 0,380: metade dos relevantes fica fora dos 10 primeiros. O primeiro resultado costuma ser relevante (MRR de 0,850). Aqui a medida é a mais frágil: o juiz leu só os resumos, os temas são largos (a q095 tem 18 relevantes), e a fronteira do que é relevante é mais subjetiva.

### Próximos experimentos, na ordem que os números sugerem

1. **BM25 e busca híbrida com RRF.** Ataca os termos raros (q067) e pode trazer o parágrafo exato nas consultas de detalhe, que repetem palavras do texto. Não deve ajudar o português.
2. **Prefixo de contexto no pedaço (título e seção), o *contextual retrieval* do livro.** Um parágrafo solto ("we use the full dataset") não diz de que artigo é, e o prefixo pode levar os pedaços certos ao topo nos detalhes e nos temas.
3. **Outros modelos (`BAAI/bge-m3`, `Qwen/Qwen3-Embedding-0.6B`).** É onde o viés de língua pode mudar, e a GPU torna o teste barato (o e5-base levou 50 s).
4. **Tamanho do pedaço.** O rótulo por trecho não depende da divisão, e a comparação é direta.
