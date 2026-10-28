# Indexação: dos artigos aos vetores

Como o [corpus](corpus.md) vira o índice que a busca consulta: os artigos são divididos em pedaços, cada pedaço vira um embedding, e os embeddings vão para a vector store. Cada escolha aqui é um ponto de partida, a ser confirmado ou trocado pelas [consultas de avaliação](avaliacao.md).

## 1. Pedaços (chunks)

O código está em `src/semantic_search/chunking.py`.

- **Um pedaço por parágrafo do corpo, e um com o título e o resumo de cada artigo.** O parágrafo é a unidade natural do texto. O livro (Chip Huyen, *AI Engineering*, 2025, cap. 6) recomenda partir da estrutura do documento e diz que não há tamanho de pedaço universal: é preciso experimentar.
- **Parágrafos de mais de 200 palavras são divididos entre frases.** O limite do modelo de partida é de 512 tokens, e o que passa disso é cortado em silêncio: o fim do parágrafo nunca seria encontrado. No corpus, uma palavra dá cerca de 1,8 token, porque fórmulas e nomes quebram em muitos tokens. Assim, 200 palavras ficam perto de 360 tokens. A divisão não quebra em abreviações ("et al.", "e.g.") nem em números ("0.87").
- **O teto é em palavras, e não em tokens de um modelo.** Todos os modelos comparados recebem os mesmos pedaços, e a diferença entre eles mede só o modelo.
- **Cada pedaço guarda o artigo, a seção e a posição do parágrafo,** a mesma posição usada nas evidências das consultas de detalhe.
- **Sem contexto do documento no início do pedaço (título, seção).** É uma das otimizações do livro (*contextual retrieval*), e entra como experimento medido, não na partida.

| | |
| --- | --- |
| Pedaços | 5.398: 100 de título e resumo, 5.298 de parágrafo |
| Parágrafos divididos | 205 de 5.038 |
| Palavras por pedaço | mediana 76, 99% com até 196; 2 pedaços passam de 200 (uma frase só, longa) |

## 2. Embeddings

O código está em `src/semantic_search/embeddings.py`.

```bash
uv run semantic-search-embed --model intfloat/multilingual-e5-base
```

- **Modelo local, pelo sentence-transformers (sobre o `transformers` da Hugging Face), como a dica do enunciado sugere.** Roda sem chave, sem custo por consulta e sem mandar o texto para fora.
- **Modelo de partida: `intfloat/multilingual-e5-base`.**
  - Multilíngue, porque metade das consultas de avaliação é em português sobre artigos em inglês.
  - Licença MIT, 278 milhões de parâmetros, vetores de 768 dimensões e limite de 512 tokens.
  - Está entre os modelos multilíngues mais baixados da Hugging Face.
  - Os candidatos para a comparação são o `BAAI/bge-m3` e o `Qwen/Qwen3-Embedding-0.6B`, maiores e mais novos.
- **Prefixos de consulta e de documento.** O e5 foi treinado com `query: ` antes da consulta e `passage: ` antes do documento, mas a configuração dele no sentence-transformers vem com os dois vazios. Sem a correção, consulta e documento saíam com o mesmo embedding, e o modelo rodaria fora do jeito em que foi treinado, sem nenhum erro aparente. Os prefixos ficam numa tabela por família de modelo, com teste. Modelos que trazem os próprios prompts, como o Qwen3-Embedding, ficam fora da tabela.
- **Vetores normalizados (norma 1).** O produto interno entre dois deles é a similaridade de cosseno, a medida que a vector store usa para comparar a consulta com os pedaços.
- **Um índice por modelo,** em `data/index/<modelo>/`: os pedaços em `chunks.jsonl`, os vetores em `embeddings.npy` (a linha *i* é o pedaço *i*) e o modelo e o corte em `meta.json`. A pasta fica fora do git e é refeita pelo comando acima.

| `multilingual-e5-base` | |
| --- | --- |
| Vetores | 5.398 × 768, 16,6 MB em float32 |
| Tempo | 987 s na CPU (Intel i7-10700K, 16 threads), cerca de 5,5 pedaços por segundo |

A geração roda na CPU porque o PyTorch instalado pelo PyPI no Windows é só para CPU. Os modelos candidatos têm 2 a 3 vezes mais parâmetros e devem levar de 40 minutos a 1 hora cada nessa máquina. Para a comparação, vale testar a versão com CUDA do PyTorch na GPU disponível (GTX 1050 Ti, 4 GB).

## 3. Vector store

Próxima etapa.
