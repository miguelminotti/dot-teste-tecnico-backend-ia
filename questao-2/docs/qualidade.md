# Qualidade da questão 2: testes e bugs

O que os testes protegem e o registro dos bugs encontrados. Para rodar: `uv run pytest`, na pasta da questão.

## Política da suíte

A mesma da [questão 1](../../questao-1/docs/qualidade.md): cada teste protege uma regra ou um caso de borda conhecido, só vale se fica vermelho com a regra quebrada, e todo bug vira teste antes da correção.

## O que cada suíte cobre

| Arquivo | Regras protegidas |
| --- | --- |
| `test_cli.py` | pergunta com acento vinda de pipe chega intacta e a resposta sai em UTF-8; sem a chave do LangSmith, o tracing é desligado, e com ela fica como está |
| `test_settings.py` | a busca na documentação liga e desliga pela variável, e vazio fica com o padrão (ligada); valor desconhecido é erro, e não busca desligada em silêncio; modelo que não aceita a busca com a busca ligada é erro na subida |
| `test_tutor.py` | a pergunta seguinte chega ao modelo com os turnos anteriores; cada chamada começa com exatamente o que a anterior enviou (o cache de prompt depende disso); pergunta que falhou não entra no histórico; com a busca ligada, ela chega ao modelo restrita aos domínios oficiais; sem a busca, nem a ferramenta nem a regra dela chegam ao modelo (o braço de controle do experimento); as páginas citadas pela busca aparecem no fim da resposta, uma vez cada |
| `evaluation/test_snippets.py` | só blocos `python` e `py` são executados, na ordem; snippet que roda passa e o que lança exceção falha com a última linha do erro; roda na versão do Python pedida; pacote de fora da biblioteca padrão é pulado, módulo removido da biblioteca padrão é falha; laço infinito falha por tempo limite; o snippet não recebe as chaves da OpenAI e do LangSmith; snippet que imprime acento passa no Windows; bloco que continua o anterior da mesma resposta passa; bloco que falhou não derruba os seguintes; bloco que depende de um pulado é pulado também, e o independente roda; marcação da linguagem em qualquer caixa e `python3`; bloco recuado dentro de item de lista roda; o snippet acha a pasta do usuário |
| `evaluation/test_run.py` | o nome do dataset não muda com o final de linha do checkout; envio interrompido (Ctrl+C) não deixa dataset vazio para trás; o resumo de uso de um experimento em que toda conversa deu erro não quebra |
| `evaluation/test_scoring.py` | cobertura contada por ponto-chave, e não por turno; ponto ausente não é erro factual; erro factual reprova mesmo com cobertura total; o comentário nomeia os pontos que faltaram |
| `evaluation/test_usage.py` | tokens do cache cobrados pelo preço de cache (conferido com o custo que o LangSmith registrou); cada busca cobrada à parte dos tokens; o uso do turno soma todas as respostas e conta só os blocos de busca; modelo sem preço é erro, não custo zero; taxa de acerto do cache ponderada por token; percentil devolve um valor que ocorreu |

O juiz não tem teste automatizado: o que ele julga só se confere contra rótulos humanos (calibração, em [avaliacao.md](avaliacao.md#como-o-juiz-decide)). Antes do experimento, ele foi conferido com uma resposta errada de propósito ("use `lista.push`"), reprovada em correção, resposta à pergunta, exemplos e nível de detalhe.

Os testes do `Tutor` usam um modelo falso próprio, que grava as mensagens de cada chamada: o que está em teste é o que vai ao modelo, sem rede nem custo. Os modelos falsos prontos do `langchain-core` não servem: eles respondem, mas descartam as mensagens que recebem, e nenhum falha numa chamada escolhida fora do streaming. Um modelo pronto com um callback do LangChain gravando as mensagens daria o mesmo resultado com código de tamanho parecido, e a falha ainda pediria um iterador que lança exceção, mais difícil de ler.

## Regras quebradas de propósito

Uma por vez; em todas a suíte falhou.

- **Tutor:** não passar o histórico; pôr o turno no histórico antes da resposta; pôr o histórico depois da pergunta; inserir o turno novo no começo do histórico. Este último só o teste do prefixo pega: a conversa continua com todos os turnos, só que em outra ordem, e o cache deixaria de funcionar sem nenhum outro sintoma.
- **CLI:** desfazer a configuração de UTF-8.
- **Execução dos snippets:** passar o ambiente inteiro ao snippet; achar o Python sem `--system` (pega o do `.venv`); tirar o `-X utf8`; pular todo módulo ausente como dependência externa; executar blocos de qualquer linguagem. A penúltima escapou na primeira rodada: o teste usava `from tkinter import nao_existe`, que dá `ImportError`, e não `ModuleNotFoundError`, então nunca passava pela regra. Ele foi trocado pelo `import cgi` no 3.14, que é o caso real (módulo removido da biblioteca padrão).
- **Sequência dos snippets:** rodar cada bloco sozinho; deixar o bloco que falhou entrar no contexto dos seguintes.
- **Notas do juiz:** contar a cobertura pela média dos turnos; reprovar a precisão factual quando falta um ponto-chave; pôr no comentário os pontos cobertos em vez dos que faltaram.
- **Métricas de uso:** cobrar o cache pelo preço cheio; dar preço zero a modelo fora da tabela; calcular a taxa de acerto do cache como média das taxas por turno; não cobrar a busca; contar todo bloco da resposta como busca.
- **Revisão final:** marcação da linguagem sensível à caixa; bloco recuado sem tirar o recuo; bloco pulado de volta no contexto; `NameError` depois de bloco pulado contado como falha; ambiente sem a pasta do usuário; modelo sem busca aceito com a busca ligada; hash dos bytes crus do dataset; `except Exception` no envio do dataset; resumo de uso sem a guarda de lista vazia; tracing que continua ligado sem chave.
- **Busca na documentação:** tirar o filtro de domínios; pôr a ferramenta ou a regra dela no braço sem busca; descartar as fontes; repetir a mesma fonte; ler um valor desconhecido da variável como desligado; ler `true` como desligado.

## Bugs registrados

Cada bug tem um teste que o reproduziu antes da correção.

### 1. Acentos corrompidos com a entrada redirecionada

- **Bug:** com a pergunta vinda de um pipe ou de um arquivo, "Olá, é?" chegava ao chatbot como "OlÃ¡, Ã©?", e as respostas saíam com os acentos trocados.
- **Como apareceu:** testando a CLI na mão com `printf ... | uv run chatbot`. Com stdin e stdout redirecionados, o Python no Windows usa a página de código do sistema (cp1252) em vez de UTF-8. No console interativo não acontece, porque ali o Python usa a API de console do Windows, que já é Unicode.
- **Teste:** `test_piped_accented_question_reaches_the_answer_intact`, que roda o processo de verdade com `PYTHONIOENCODING=cp1252` para reproduzir o padrão do Windows em qualquer sistema. Ele roda o laço da conversa com uma resposta fixa no lugar do modelo, para não depender de chave nem de rede; por isso confere o `use_utf8_stdio`, e não a chamada a ele dentro do `main`.
- **Correção:** o `main` reconfigura stdin, stdout e stderr para UTF-8 (`use_utf8_stdio`) antes de começar a conversa.

### 2. Snippets rodavam com as dependências do chatbot

- **Bug:** o executor achava o Python pelo `uv python find`, que, dentro do projeto, devolve o do `.venv`. Os snippets rodavam com Pydantic, LangChain e o resto das dependências do chatbot disponíveis: um `import pydantic` passava na avaliação e falharia na máquina do aluno.
- **Como apareceu:** escrevendo os testes do executor, antes do primeiro experimento. `test_third_party_import_is_skipped_not_failed` falhou.
- **Correção:** `uv python find --system`, que ignora ambientes virtuais.

### 3. Snippet com acento falhava por encoding

- **Bug:** um snippet com `print('ação')` falhava com `UnicodeEncodeError` no Windows, e contaria como código errado. O executor passava `PYTHONIOENCODING=utf-8` ao snippet, mas o modo isolado (`-I`) ignora as variáveis `PYTHON*`.
- **Como apareceu:** no mesmo lote de testes, com `test_snippet_that_prints_accents_passes`.
- **Correção:** o modo UTF-8 vai na linha de comando (`-X utf8`), que o `-I` respeita.

### 4. Bloco que dependia de pacote externo contava como falha

- **Bug:** com os blocos de uma resposta rodando em sequência, o bloco do `from pydantic import BaseModel` era pulado (dependência externa) e ficava fora da sequência. O bloco seguinte, que usa o `BaseModel`, falhava com `NameError` e contava como código errado numa resposta sobre a biblioteca.
- **Como apareceu:** lendo as falhas de snippet da segunda linha de base (`gpt-4.1-mini-4e2c001d`), na conversa do Pydantic.
- **Teste:** `test_block_that_needs_a_skipped_dependency_is_skipped_too`.
- **Correção:** o bloco pulado fica na sequência; o que vem depois esbarra na mesma dependência e é pulado também. Só o bloco que falhou fica de fora.

### 5. Modelo sem busca com a busca ligada falhava em toda pergunta

- **Bug:** com `CHATBOT_MODEL=gpt-4.1-mini` e a busca no padrão (ligada), a API recusava toda chamada, e a CLI respondia "Tente de novo" a cada pergunta, sem que tentar de novo resolvesse.
- **Como apareceu:** na revisão final, rodando a CLI com um `.env` antigo, que ainda fixava o `gpt-4.1-mini`; o revisor independente achou o mesmo caminho lendo o código. O `gpt-4.1-nano` foi conferido junto: recusa a própria ferramenta de busca.
- **Teste:** `test_model_that_rejects_the_docs_search_is_an_error_at_startup`.
- **Correção:** a configuração barra a combinação na subida, com a mensagem dizendo o que fazer.

### 6. Executor de snippets: bloco recuado, bloco pulado e pasta do usuário

- **Bug:** três casos contavam código certo como errado ou escondiam um erro. Um bloco dentro de item de lista vinha com o recuo do markdown e falhava com `IndentationError`. Um bloco pulado por dependência externa entrava no contexto dos seguintes, e o `import` dele pulava todos, inclusive um independente com erro de verdade. E `Path.home()` falhava porque o ambiente do snippet não tinha a pasta do usuário. Blocos marcados ` ```Python ` ou ` ```python3 ` nem eram executados.
- **Como apareceu:** na revisão final, pelo revisor independente, que reproduziu cada caso rodando o executor.
- **Testes:** `test_block_indented_inside_a_list_item_runs`, `test_independent_block_after_a_skipped_one_still_runs`, `test_snippet_can_find_the_home_directory` e `test_language_tag_ignores_case_and_accepts_python3`.
- **Correção:** o recuo comum sai antes de rodar; o bloco pulado fica fora do contexto, e só o bloco seguinte que falha com `NameError` é pulado junto; `HOME` e `USERPROFILE` entram no ambiente; a marcação da linguagem ignora a caixa e aceita `python3`.

### 7. Dataset e resumo do experimento

- **Bug:** três falhas da avaliação. O nome do dataset vinha do hash dos bytes do arquivo, e o git troca o final de linha no checkout, então o mesmo dataset teria um nome no Windows e outro no Linux. Um Ctrl+C no meio do envio deixava o dataset criado e vazio, reaproveitado para sempre. E num experimento em que toda conversa dá erro, o resumo de uso quebrava com lista vazia, escondendo o erro de verdade.
- **Como apareceu:** na revisão final, pelo revisor independente; o CRLF do arquivo foi conferido nesta máquina.
- **Testes:** `test_dataset_name_does_not_depend_on_line_endings`, `test_interrupted_upload_does_not_leave_an_empty_dataset` e `test_usage_summary_of_an_experiment_where_every_conversation_failed`.
- **Correção:** o hash normaliza o final de linha; o envio apaga o dataset em qualquer interrupção (`BaseException`); o resumo sem turnos não devolve nota.

### 8. Avisos do LangSmith no meio da conversa

- **Bug:** o `.env.example` vem com o tracing ligado. Quem preenchia só a chave da OpenAI via avisos e erros 401 do LangSmith misturados às respostas.
- **Como apareceu:** na revisão final, apontado pelo revisor como plausível e reproduzido rodando a CLI.
- **Teste:** `test_tracing_without_langsmith_key_is_turned_off`.
- **Correção:** sem a chave do LangSmith, a CLI desliga o tracing e avisa numa linha.
