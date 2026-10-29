# Qualidade da questão 2: testes e bugs

O que os testes protegem e o registro dos bugs encontrados. Para rodar: `uv run pytest`, na pasta da questão.

## Política da suíte

A mesma da [questão 1](../../questao-1/docs/qualidade.md): cada teste protege uma regra ou um caso de borda conhecido, só vale se fica vermelho com a regra quebrada, e todo bug vira teste antes da correção.

Os testes do `Tutor` usam um modelo falso próprio, que grava as mensagens de cada chamada: o que está em teste é o que vai ao modelo, sem rede nem custo. O juiz não tem teste automatizado: o que ele julga só se confere contra rótulos humanos, e a calibração ainda não foi feita ([avaliacao.md](avaliacao.md#métricas)).

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

### 9. Chave inválida virava "tente de novo"

- **Bug:** com a chave errada, sem permissão ou sem saldo, cada pergunta respondia "Não consegui responder agora (AuthenticationError). Tente de novo." e a conversa seguia, com toda pergunta falhando. A subida só confere se a chave existe, não se ela vale.
- **Como apareceu:** numa segunda revisão independente, depois da entrega das três questões, simulada com um modelo falso que levanta o erro da OpenAI.
- **Testes:** `test_rejected_key_or_account_is_not_reported_as_a_passing_failure`, `test_rate_limit_is_a_passing_failure` e `test_rejected_key_or_account_ends_the_chat`.
- **Correção:** 401, 403 e 429 com `insufficient_quota` viram erro de configuração, e a CLI sai com a mensagem e código 1. O 429 de limite por minuto continua como falha passageira.

### 10. Modelo sem acesso e contexto estourado também viravam "tente de novo"

- **Bug:** a correção do bug 9 cobriu a chave e a conta, mas não a requisição. Com um `CHATBOT_MODEL` a que a chave não tem acesso (404 `model_not_found`) ou com o histórico maior que o contexto do modelo (400), cada pergunta respondia "Não consegui responder agora (NotFoundError). Tente de novo.", sem o motivo, e nenhuma tentativa passava: o histórico só cresce.
- **Como apareceu:** na terceira revisão independente, com o mesmo modelo falso.
- **Testes:** `test_request_the_api_will_always_reject_is_not_reported_as_a_passing_failure` e `test_request_the_api_will_always_reject_ends_the_chat`.
- **Correção:** 400, 404 e 422 encerram a conversa com a mensagem da API ("The model ... does not exist", "... context window"), que diz o que mudar.

### 11. A suíte falhava sem o Python 3.14

- **Bug:** o teste do módulo removido da biblioteca padrão roda no 3.14, que o `uv sync` não instala. Numa máquina sem ele, `uv run pytest` falhava com "Python 3.14 não encontrado", e os portões de qualidade não passavam para quem clonou o repositório.
- **Como apareceu:** na terceira revisão independente, simulando a máquina sem o 3.14 com `UV_PYTHON_PREFERENCE=only-managed`.
- **Correção:** sem o 3.14, o teste é pulado com o comando que o instala no motivo.
