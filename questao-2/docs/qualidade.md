# Qualidade da questão 2: testes e bugs

O que os testes protegem e o registro dos bugs encontrados. Para rodar: `uv run pytest`, na pasta da questão.

## Política da suíte

A mesma da [questão 1](../../questao-1/docs/qualidade.md): cada teste protege uma regra ou um caso de borda conhecido, só vale se fica vermelho com a regra quebrada, e todo bug vira teste antes da correção.

## Bugs registrados

Cada bug tem um teste que o reproduziu antes da correção.

### 1. Acentos corrompidos com a entrada redirecionada

- **Bug:** com a pergunta vinda de um pipe ou de um arquivo, "Olá, é?" chegava ao chatbot como "OlÃ¡, Ã©?", e as respostas saíam com os acentos trocados.
- **Como apareceu:** testando a CLI na mão com `printf ... | uv run chatbot`. Com stdin e stdout redirecionados, o Python no Windows usa a página de código do sistema (cp1252) em vez de UTF-8. No console interativo não acontece, porque ali o Python usa a API de console do Windows, que já é Unicode.
- **Teste:** `test_piped_accented_question_reaches_the_answer_intact`, que roda o processo de verdade com `PYTHONIOENCODING=cp1252` para reproduzir o padrão do Windows em qualquer sistema.
- **Correção:** o `main` reconfigura stdin, stdout e stderr para UTF-8 antes de começar a conversa.
