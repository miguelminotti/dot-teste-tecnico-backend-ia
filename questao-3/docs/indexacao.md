# Indexação: dos artigos aos vetores

Como o [corpus](corpus.md) vira o índice que a busca consulta: os artigos são divididos em pedaços, cada pedaço vira um embedding, e os embeddings vão para a vector store. Cada escolha aqui é um ponto de partida, a ser confirmado ou trocado pelas [consultas de avaliação](avaliacao.md).

## 1. Pedaços (chunks)

O código está em `src/semantic_search/chunking.py`.

- **Um pedaço por parágrafo do corpo, e um com o título e o resumo de cada artigo.** O parágrafo é a unidade natural do texto. O livro (Chip Huyen, *AI Engineering*, 2025, cap. 6) recomenda partir da estrutura do documento e diz que não há tamanho de pedaço universal: é preciso experimentar.
- **Parágrafos de mais de 200 palavras são divididos entre frases, e o título com o resumo também.** O limite do e5-base é de 512 tokens, e o que passa disso é cortado em silêncio: o fim do parágrafo nunca seria encontrado. No corpus, uma palavra dá em média 1,8 token no tokenizador do e5, porque fórmulas e nomes quebram em muitos tokens. Assim, 200 palavras ficam, em média, perto de 360 tokens. A média esconde as exceções: 40 pedaços, todos parágrafos com fórmulas em LaTeX, passam dos 512 tokens do e5 (o maior tem 1.022) e perdem o fim quando indexados por ele. O bge-m3, o modelo padrão, aceita até 8.192 tokens e não corta nenhum. A divisão não quebra em abreviações ("et al.", "e.g.") nem em números ("0.87").
- **O teto é em palavras, e não em tokens de um modelo.** Todos os modelos comparados recebem os mesmos pedaços, e a diferença entre eles mede só o modelo.
- **Cada pedaço guarda o artigo, a seção e a posição do parágrafo,** a mesma posição usada nas evidências das consultas de detalhe.
- **Sem contexto do documento no início do pedaço (título, seção).** É uma das otimizações do livro (*contextual retrieval*), e entra como experimento medido, não na partida.

| | |
| --- | --- |
| Pedaços | 5.032: 155 de título e resumo (55 artigos têm título e resumo com mais de 200 palavras, divididos em dois pedaços), 4.877 de parágrafo |
| Parágrafos divididos | 190 de 4.672 |
| Palavras por pedaço | mediana 79, 99% com até 197; 2 pedaços passam de 200 (uma frase só, longa) |

## 2. Embeddings

O código está em `src/semantic_search/embeddings.py`.

```bash
uv run semantic-search-embed
uv run semantic-search-embed --model intfloat/multilingual-e5-base
```

- **Modelo local, pelo sentence-transformers (sobre o `transformers` da Hugging Face), como a dica do enunciado sugere.** Roda sem chave, sem custo por consulta e sem mandar o texto para fora. O modelo precisa ser multilíngue, porque metade das consultas de avaliação é em português sobre artigos em inglês.
- **Modelo padrão: `BAAI/bge-m3`** ([ADR 0001](adr/0001-modelo-de-embeddings-bge-m3.md)). Licença MIT, 568 milhões de parâmetros e vetores de 1.024 dimensões. Não usa prefixo de consulta nem de documento.
- **Opção leve: `intfloat/multilingual-e5-base`,** o modelo de partida. Licença MIT, 278 milhões de parâmetros, vetores de 768 dimensões e limite de 512 tokens. Indexa em um quarto do tempo do bge-m3 na CPU, mas em português põe no topo, com frequência, um artigo sobre LLM brasileiro no lugar do certo ([experimentos](experimentos.md#outro-modelo-bge-m3)).
- **Prefixos de consulta e de documento.** O e5 foi treinado com `query: ` antes da consulta e `passage: ` antes do documento, mas a configuração dele no sentence-transformers vem com os dois vazios. Sem a correção, consulta e documento saíam com o mesmo embedding, e o modelo rodaria fora do jeito em que foi treinado, sem nenhum erro aparente. Os prefixos ficam numa tabela por família de modelo, com teste. Modelos que trazem os próprios prompts, como o Qwen3-Embedding, ficam fora da tabela.
- **Vetores normalizados (norma 1).** O produto interno entre dois deles é a similaridade de cosseno, a medida que a vector store usa para comparar a consulta com os pedaços.
- **Um índice por modelo,** em `data/index/<modelo>/`: os pedaços em `chunks.jsonl`, os vetores em `embeddings.npy` (a linha *i* é o pedaço *i*) e o modelo e o corte em `meta.json`. A pasta fica fora do git e é refeita pelo comando acima.

| | `bge-m3` | `multilingual-e5-base` |
| --- | --- | --- |
| Vetores | 5.032 × 1.024, 20,6 MB em float32 | 5.032 × 768, 15,5 MB em float32 |
| Download do modelo | 4,3 GB | 1,1 GB |
| Tempo na GPU (NVIDIA RTX 3060, 12 GB) | 152 s | 48 s |
| Tempo na CPU | cerca de 85 min (Intel i7-4790K, estimado por uma amostra de 200 pedaços) | cerca de 22 min no i7-4790K, pela mesma amostra; 987 s num Intel i7-10700K (16 threads), na primeira versão do corpus, com 5.398 pedaços |

**CPU por padrão, GPU opcional.** O `uv.lock` fixa o PyTorch do PyPI, que no Windows é só para CPU: o projeto roda em qualquer máquina, sem CUDA. Com uma GPU NVIDIA, a versão com CUDA entra só no `.venv`, sem mudar o projeto, e os comandos passam a usar `--no-sync`, porque um `uv run` comum sincroniza o ambiente com o `uv.lock` e volta o PyTorch para a versão de CPU. O índice sai igual nos dois casos.

```bash
uv pip install --reinstall-package torch "torch==2.15.0" --index-url https://download.pytorch.org/whl/cu132
uv run --no-sync semantic-search-embed
```

## 3. Vector store

O código está em `src/semantic_search/vector_store.py`.

```bash
uv run semantic-search-store
```

- **FAISS, e não Milvus.** O enunciado aceita os dois. O FAISS é uma biblioteca: roda no mesmo processo da busca e grava o índice num arquivo. O Milvus é um banco de vetores, feito para rodar como serviço, que se paga com milhões de vetores, filtros por metadado e escrita concorrente. Nada disso existe aqui: são 5 mil vetores, gravados uma vez e só lidos depois.
- **Busca exata (`IndexFlatIP`).** A consulta é comparada com todos os vetores pelo produto interno, que, com vetores de norma 1, é a similaridade de cosseno. O livro (cap. 6) apresenta os índices aproximados (HNSW, IVF, PQ) como uma troca de recall por velocidade, que compensa em escala. Com 5 mil vetores, a busca exata leva poucos milissegundos (tabela abaixo) e devolve os vizinhos certos, sem parâmetro para ajustar.
- **Vetores sem norma 1 são recusados.** Sem ela, o produto interno deixa de ser o cosseno, e um vetor longo venceria a busca por ser longo. A consulta não precisa da checagem: a norma dela multiplica todas as notas pelo mesmo fator e não muda a ordem.
- **Os pedaços ficam fora do FAISS.** O índice guarda só os vetores, e o resultado é a posição: o vetor *i* é a linha *i* do `chunks.jsonl`. Ao carregar, o número de vetores é conferido com o de pedaços, o que pega um `faiss.index` velho ao lado de pedaços regerados.
- **Com menos pedaços que o `k` pedido, a busca devolve só os que existem.** O FAISS completa as vagas com a posição -1, que em Python apontaria para o último pedaço.
- **O índice é gravado como `faiss.index`** na pasta do modelo, ao lado dos pedaços, fora do git, e o comando acima o refaz em menos de 1 segundo. No índice exato, o arquivo é a própria matriz de vetores, do mesmo tamanho do `embeddings.npy`. O índice passa por bytes e é gravado pelo Python, e não pelo FAISS: no Windows, o FAISS não abre caminho com acento, como o de um usuário `C:\Users\João`.

| `IndexFlatIP` | `bge-m3` | `multilingual-e5-base` |
| --- | --- | --- |
| Montagem | 0,11 s | 0,09 s |
| Tamanho | 20,6 MB, o mesmo da matriz em float32 | 15,5 MB, o mesmo da matriz em float32 |
| Busca dos 10 mais próximos, uma consulta por vez, na CPU (Intel i7-4790K, 8 threads) | mediana de 1,7 ms | mediana de 1,2 ms |
| Busca das 198 consultas de avaliação (99 em inglês e 99 em português) em lote | 17,8 ms | 15,5 ms |
| Embedding de uma consulta, na GPU (RTX 3060), mediana | 23,2 ms | 12,5 ms |
| Conferência com numpy (produto interno com todos os vetores, ordenado) | os mesmos 10 pedaços, na mesma ordem, nas 198 consultas | os mesmos 10 pedaços, na mesma ordem, nas 198 consultas |

As latências da busca variam entre rodadas: a mediana do e5-base foi de 2,5 ms numa medida e de 1,2 ms em outra. Nas duas, a busca exata fica na casa de 1 a 3 ms, menor que o embedding da consulta.
