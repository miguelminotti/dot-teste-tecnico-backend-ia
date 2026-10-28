# Qualidade da questão 2: testes e bugs

O que os testes protegem e o registro dos bugs encontrados. Para rodar: `uv run pytest`, na pasta da questão.

## Política da suíte

A mesma da [questão 1](../../questao-1/docs/qualidade.md): cada teste protege uma regra ou um caso de borda conhecido, só vale se fica vermelho com a regra quebrada, e todo bug vira teste antes da correção.

## O que cada suíte cobre

| Arquivo | Regras protegidas |
| --- | --- |
| `test_cli.py` | pergunta com acento vinda de pipe chega intacta e a resposta sai em UTF-8 |
| `test_tutor.py` | a pergunta seguinte chega ao modelo com os turnos anteriores; cada chamada começa com exatamente o que a anterior enviou (o cache de prompt depende disso); pergunta que falhou não entra no histórico |
| `evaluation/test_snippets.py` | só blocos `python` e `py` são executados, na ordem; snippet que roda passa e o que lança exceção falha com a última linha do erro; roda na versão do Python pedida; pacote de fora da biblioteca padrão é pulado, módulo removido da biblioteca padrão é falha; laço infinito falha por tempo limite; o snippet não recebe as chaves da OpenAI e do LangSmith; snippet que imprime acento passa no Windows; bloco que continua o anterior da mesma resposta passa; bloco que falhou não derruba os seguintes; bloco que depende de um pulado é pulado também |
| `evaluation/test_scoring.py` | cobertura contada por ponto-chave, e não por turno; ponto ausente não é erro factual; erro factual reprova mesmo com cobertura total; o comentário nomeia os pontos que faltaram |
| `evaluation/test_usage.py` | tokens do cache cobrados pelo preço de cache (conferido com o custo que o LangSmith registrou); modelo sem preço é erro, não custo zero; taxa de acerto do cache ponderada por token; percentil devolve um valor que ocorreu |

O juiz não tem teste automatizado: o que ele julga só se confere contra rótulos humanos (calibração, em [avaliacao.md](avaliacao.md#como-o-juiz-decide)). Antes do experimento, ele foi conferido com uma resposta errada de propósito ("use `lista.push`"), reprovada em correção, resposta à pergunta, exemplos e nível de detalhe.

Os testes do `Tutor` usam um modelo falso próprio, que grava as mensagens de cada chamada: o que está em teste é o que vai ao modelo, sem rede nem custo. Os modelos falsos prontos do `langchain-core` não servem: eles respondem, mas descartam as mensagens que recebem, e nenhum falha numa chamada escolhida fora do streaming. Um modelo pronto com um callback do LangChain gravando as mensagens daria o mesmo resultado com código de tamanho parecido, e a falha ainda pediria um iterador que lança exceção, mais difícil de ler.

## Regras quebradas de propósito

Uma por vez; em todas a suíte falhou.

- **Tutor:** não passar o histórico; pôr o turno no histórico antes da resposta; pôr o histórico depois da pergunta; inserir o turno novo no começo do histórico. Este último só o teste do prefixo pega: a conversa continua com todos os turnos, só que em outra ordem, e o cache deixaria de funcionar sem nenhum outro sintoma.
- **CLI:** desfazer a configuração de UTF-8.
- **Execução dos snippets:** passar o ambiente inteiro ao snippet; achar o Python sem `--system` (pega o do `.venv`); tirar o `-X utf8`; pular todo módulo ausente como dependência externa; executar blocos de qualquer linguagem. A penúltima escapou na primeira rodada: o teste usava `from tkinter import nao_existe`, que dá `ImportError`, e não `ModuleNotFoundError`, então nunca passava pela regra. Ele foi trocado pelo `import cgi` no 3.14, que é o caso real (módulo removido da biblioteca padrão).
- **Sequência dos snippets:** rodar cada bloco sozinho; deixar o bloco que falhou entrar no contexto dos seguintes.
- **Notas do juiz:** contar a cobertura pela média dos turnos; reprovar a precisão factual quando falta um ponto-chave; pôr no comentário os pontos cobertos em vez dos que faltaram.
- **Métricas de uso:** cobrar o cache pelo preço cheio; dar preço zero a modelo fora da tabela; calcular a taxa de acerto do cache como média das taxas por turno.

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
