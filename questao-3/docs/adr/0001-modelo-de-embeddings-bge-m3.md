# ADR 0001: Embeddings com o bge-m3

- **Status:** Aceita
- **Data:** 2026-10-28

## Contexto

O modelo de embeddings define o índice inteiro: trocar de modelo é gerar de novo os vetores de todos os pedaços, e as instruções de reprodução, os tempos e os números citados na documentação mudam junto.

O corpus é de artigos em inglês, e metade das consultas de avaliação é em português sobre esses artigos. O modelo precisa ser multilíngue e rodar localmente, como a dica do enunciado sugere, sem chave e sem mandar o texto para fora.

O ponto de partida foi o `intfloat/multilingual-e5-base`. A avaliação mostrou um erro sistemático dele em português: um artigo sobre um LLM em português brasileiro ficava em 1º, no lugar do artigo certo, em 10 das 99 buscas em português. O embedding casava a língua da consulta com o assunto "português". A busca híbrida com BM25 não resolveu, porque o BM25 não tem palavra para casar entre as duas línguas, e piorou esse caso.

O `BAAI/bge-m3`, medido nas mesmas consultas e sobre os mesmos pedaços ([experimentos](../experimentos.md#outro-modelo-bge-m3)):

- leva esse erro de 10 casos para 1;
- reduz de 14 para 6 as consultas em que o português perde para o inglês;
- acerta em 1º, nas duas línguas, um termo raro que o e5 punha em 10º;
- empata com o e5 nas médias. O MRR total vai de 0,920 para 0,933, e a R-precision fica igual. Num bootstrap pareado, as diferenças ficam dentro do ruído de 99 consultas.

O custo é o de um modelo com o dobro de parâmetros: a consulta leva o dobro do tempo (23 ms contra 12,5 ms na GPU), o download passa de 1,1 GB para 4,3 GB, e a indexação do corpus sem GPU passa de cerca de 22 para cerca de 84 minutos numa CPU de 2014. Com GPU, ela leva menos de 3 minutos.

## Decisão

- O `BAAI/bge-m3` é o modelo padrão da indexação, da busca e da avaliação.
- O `intfloat/multilingual-e5-base` continua suportado e documentado como a opção leve, para quem indexa sem GPU e aceita o erro do português.
- A busca padrão continua só com embeddings: a híbrida perde em português também com o bge-m3.

## Alternativas consideradas

- **Manter o e5-base:** as médias empatam, o índice sai em um quarto do tempo na CPU, e o download é um quarto do tamanho. Mas o erro que ele deixa é sistemático e fica à vista: quem busca em português recebe, no topo, um artigo sobre LLM brasileiro no lugar do que pediu. Uma média que não separa os modelos não compensa um defeito que se repete.
- **Qwen3-Embedding-0.6B:** é mais novo e do mesmo porte do bge-m3, mas não foi medido. A pergunta era se outro modelo resolve o viés de língua, e o bge-m3 respondeu. Com 99 consultas, comparar vários modelos tenderia a escolher o que se ajusta a este conjunto, e não o melhor para a busca.
- **Embeddings por API (OpenAI e outros):** dispensam a indexação local e o download, mas cada consulta e o corpus inteiro saem da máquina, o uso pede uma chave e tem custo por chamada, e o enunciado sugere modelos locais. Não foram medidos.
- **bge-m3 na busca híbrida:** melhora o inglês, mas em português o MRR cai de 0,924 para 0,826. Fica como opção, e não como padrão.

## Consequências

- Quem reproduz o teste baixa 4,3 GB e espera cerca de 84 minutos para indexar sem GPU, ou menos de 3 minutos com uma GPU NVIDIA. As instruções apontam o e5-base para quem quer indexar mais rápido na CPU.
- O índice de cada modelo fica numa pasta própria. Os dois convivem, e a comparação continua reproduzível.
- A linha de base dos experimentos continua registrada com o e5-base, que foi o modelo medido primeiro. Os números da indexação e da busca passam a citar o bge-m3.
- A escolha fica para ser revista se o conjunto de avaliação crescer o bastante para separar os modelos nas médias, ou se um modelo menor resolver o português com o mesmo resultado.
