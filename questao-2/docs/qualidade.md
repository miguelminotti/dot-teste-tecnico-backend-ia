# Qualidade da questão 2: testes e bugs

O que os testes protegem e o registro dos bugs encontrados. Para rodar: `uv run pytest`, na pasta da questão.

## Política da suíte

A mesma da [questão 1](../../questao-1/docs/qualidade.md): cada teste protege uma regra ou um caso de borda conhecido, só vale se fica vermelho com a regra quebrada, e todo bug vira teste antes da correção.

## O que cada suíte cobre

| Arquivo | Regras protegidas |
| --- | --- |
| `test_cli.py` | pergunta com acento vinda de pipe chega intacta e a resposta sai em UTF-8 |
| `test_tutor.py` | a pergunta seguinte chega ao modelo com os turnos anteriores; cada chamada começa com exatamente o que a anterior enviou (o cache de prompt depende disso); pergunta que falhou não entra no histórico |

Os testes do `Tutor` usam um modelo falso próprio, que grava as mensagens de cada chamada: o que está em teste é o que vai ao modelo, sem rede nem custo. Os modelos falsos prontos do `langchain-core` não servem: eles respondem, mas descartam as mensagens que recebem, e nenhum falha numa chamada escolhida fora do streaming. Um modelo pronto com um callback do LangChain gravando as mensagens daria o mesmo resultado com código de tamanho parecido, e a falha ainda pediria um iterador que lança exceção, mais difícil de ler.

## Regras quebradas de propósito

Uma por vez; em todas a suíte falhou.

- **Tutor:** não passar o histórico; pôr o turno no histórico antes da resposta; pôr o histórico depois da pergunta; inserir o turno novo no começo do histórico. Este último só o teste do prefixo pega: a conversa continua com todos os turnos, só que em outra ordem, e o cache deixaria de funcionar sem nenhum outro sintoma.
- **CLI:** desfazer a configuração de UTF-8.

## Bugs registrados

Cada bug tem um teste que o reproduziu antes da correção.

### 1. Acentos corrompidos com a entrada redirecionada

- **Bug:** com a pergunta vinda de um pipe ou de um arquivo, "Olá, é?" chegava ao chatbot como "OlÃ¡, Ã©?", e as respostas saíam com os acentos trocados.
- **Como apareceu:** testando a CLI na mão com `printf ... | uv run chatbot`. Com stdin e stdout redirecionados, o Python no Windows usa a página de código do sistema (cp1252) em vez de UTF-8. No console interativo não acontece, porque ali o Python usa a API de console do Windows, que já é Unicode.
- **Teste:** `test_piped_accented_question_reaches_the_answer_intact`, que roda o processo de verdade com `PYTHONIOENCODING=cp1252` para reproduzir o padrão do Windows em qualquer sistema. Ele roda o laço da conversa com uma resposta fixa no lugar do modelo, para não depender de chave nem de rede; por isso confere o `use_utf8_stdio`, e não a chamada a ele dentro do `main`.
- **Correção:** o `main` reconfigura stdin, stdout e stderr para UTF-8 (`use_utf8_stdio`) antes de começar a conversa.
