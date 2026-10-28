# Exemplos de perguntas e respostas

Conversas reais com o chatbot, geradas pela CLI em 2026-10-28 na configuração padrão (`gpt-5.4-mini` com busca na documentação, [ADR 0002](adr/0002-busca-na-documentacao-com-gpt-5-4-mini.md)). As respostas estão como a CLI as imprimiu, sem edição; o modelo responde diferente a cada execução, então uma nova rodada não repete o texto. Os blocos de código das respostas foram executados na versão do Python de cada pergunta.

Para gerar uma conversa assim:

```bash
uv run --env-file .env chatbot
```

## Como criar uma lista em Python? (o exemplo do enunciado)

A segunda pergunta só faz sentido com a primeira: o tutor sabe de que lista se fala porque o histórico vai junto (ADR 0001). Nenhuma das duas cita a documentação: é o básico da linguagem, que o modelo responde sem fonte. O código vem em blocos `python` e a saída em blocos `text`; todos os blocos rodam no Python 3.12, menos o `remove("banana")` na lista sem banana, que a resposta mostra de propósito para ensinar o `ValueError`. O fim ainda oferece o resto ("Se quiser, posso também te mostrar..."), como na avaliação: aqui, o construtor `list()` ficou de fora da resposta.

**Você:** Como criar uma lista em Python?

**Chatbot:**

> Em Python, uma **lista** é criada usando colchetes `[]`.
>
> ## Exemplos básicos
>
> ```python
> # lista vazia
> lista_vazia = []
>
> # lista com valores
> numeros = [1, 2, 3, 4]
>
> # lista com tipos diferentes
> misturada = [1, "dois", 3.0, True]
> ```
>
> ## Como funciona
>
> - As listas guardam **vários itens em uma única variável**.
> - A ordem dos elementos é mantida.
> - Você pode **alterar** uma lista depois de criada.
>
> ## Operações comuns
>
> ### Acessar elementos
> ```python
> frutas = ["maçã", "banana", "uva"]
>
> print(frutas[0])  # primeiro elemento
> print(frutas[1])  # segundo elemento
> ```
>
> ```text
> maçã
> banana
> ```
>
> ### Adicionar itens
> ```python
> frutas = ["maçã", "banana"]
> frutas.append("uva")
>
> print(frutas)
> ```
>
> ```text
> ['maçã', 'banana', 'uva']
> ```
>
> ### Remover itens
> ```python
> frutas = ["maçã", "banana", "uva"]
> frutas.remove("banana")
>
> print(frutas)
> ```
>
> ```text
> ['maçã', 'uva']
> ```
>
> Se quiser, posso também te mostrar **como criar listas usando `list()`**, **listas com loop**, ou **listas por compreensão**.

**Você:** E como removo um item dela?

**Chatbot:**

> Você pode remover um item de uma lista em Python de algumas formas, dependendo do que você quer fazer.
>
> ## 1) `remove(valor)`
> Remove o **primeiro item com aquele valor**.
>
> ```python
> frutas = ["maçã", "banana", "uva"]
> frutas.remove("banana")
>
> print(frutas)
> ```
>
> ```text
> ['maçã', 'uva']
> ```
>
> Se o valor não existir, ocorre erro:
>
> ```python
> frutas = ["maçã", "uva"]
> frutas.remove("banana")
> ```
>
> ```text
> ValueError: list.remove(x): x not in list
> ```
>
> ## 2) `pop(indice)`
> Remove e **retorna** o item de uma posição específica.
>
> ```python
> frutas = ["maçã", "banana", "uva"]
> item = frutas.pop(1)
>
> print(item)
> print(frutas)
> ```
>
> ```text
> banana
> ['maçã', 'uva']
> ```
>
> Se você não passar índice, ele remove o **último** item.
>
> ```python
> frutas = ["maçã", "banana", "uva"]
> item = frutas.pop()
>
> print(item)
> print(frutas)
> ```
>
> ```text
> uva
> ['maçã', 'banana']
> ```
>
> ## 3) `del`
> Remove um item pelo índice, sem retornar o valor.
>
> ```python
> frutas = ["maçã", "banana", "uva"]
> del frutas[1]
>
> print(frutas)
> ```
>
> ```text
> ['maçã', 'uva']
> ```
>
> ## 4) `clear()`
> Remove **todos** os itens da lista.
>
> ```python
> frutas = ["maçã", "banana", "uva"]
> frutas.clear()
>
> print(frutas)
> ```
>
> ```text
> []
> ```
>
> ## Resumo rápido
>
> - `remove(valor)` → remove pelo **valor**
> - `pop(indice)` → remove pelo **índice** e devolve o item
> - `del lista[indice]` → remove pelo índice
> - `clear()` → esvazia a lista inteira
>
> Se quiser, posso te mostrar também a diferença entre **remover por valor** e **remover por posição** com exemplos mais práticos.

## Recurso recente, com busca e fontes

Recurso lançado depois do corte de treinamento do modelo: ele buscou na documentação oficial, citou as páginas ao longo do texto e o tutor listou as fontes no fim. Os blocos rodam no Python 3.14, e a saída que a resposta mostra é a mesma que o 3.14 imprime, conferida à parte. Sem a busca, nas avaliações, essa pergunta saiu errada.

**Você:** O que são as template strings (t-strings) do Python 3.14?

**Chatbot:**

> As **template strings** ou **t-strings** são uma novidade do Python 3.14. Elas usam o prefixo `t` ou `T`, parecido com f-strings, mas com uma diferença importante: **em vez de produzir diretamente uma `str`, elas produzem um objeto `string.templatelib.Template`**. Esse objeto preserva separadamente as partes literais e as interpolações, para que outro código possa processá-las depois. ([docs.python.org](https://docs.python.org/3/whatsnew/3.14.html?utm_source=openai))
>
> ## Ideia principal
>
> Com f-strings, você escreve:
>
> ```python
> name = "Ana"
> msg = f"Olá, {name}!"
> ```
>
> e o resultado já é uma string pronta.
>
> Com t-strings, você escreve:
>
> ```python
> name = "Ana"
> template = t"Olá, {name}!"
> ```
>
> e o resultado é um **template** com estrutura preservada, não uma string final. ([docs.python.org](https://docs.python.org/3/whatsnew/3.14.html?utm_source=openai))
>
> ## O que vem dentro de um `Template`
>
> Um `Template` separa:
>
> - o **texto literal**;
> - cada **interpolação**;
> - informações como expressão original, conversão e especificador de formato. ([docs.python.org](https://docs.python.org/3/whatsnew/3.14.html?utm_source=openai))
>
> Exemplo:
>
> ```python
> from string.templatelib import Interpolation
>
> name = "Ana"
> template = t"Olá, {name}!"
> print(type(template))
> print(list(template))
> ```
>
> Saída esperada:
>
> ```text
> <class 'string.templatelib.Template'>
> ['Olá, ', Interpolation('Ana', 'name', None, ''), '!']
> ```
>
> ## Para que serve
>
> A utilidade dos t-strings é permitir **processamento customizado de strings**. O Python cita usos como:
>
> - sanitização de SQL;
> - operações seguras com shell;
> - logging;
> - HTML/CSS;
> - pequenas DSLs de domínio específico. ([docs.python.org](https://docs.python.org/3/whatsnew/3.14.html?utm_source=openai))
>
> A ideia é: em vez de transformar tudo em texto logo de cara, você passa a estrutura para uma função que decide como renderizar com segurança.
>
> ## Exemplo simples de processamento
>
> Você pode escrever uma função que trata cada parte de um jeito:
>
> ```python
> from string.templatelib import Interpolation
>
> def process(template):
>     parts = []
>     for part in template:
>         if isinstance(part, Interpolation):
>             parts.append(f"<{part.value}>")
>         else:
>             parts.append(part.upper())
>     return "".join(parts)
>
> name = "Ana"
> template = t"Olá, {name}!"
> print(process(template))
> ```
>
> Saída:
>
> ```text
> OLÁ, <Ana>!
> ```
>
> ## Diferenças em relação às f-strings
>
> As t-strings seguem praticamente a mesma sintaxe das f-strings, mas mudam a semântica de avaliação: em vez de gerar `str`, geram `Template`. Além disso, o protocolo `format()` não é usado diretamente; o especificador de formato e conversões vão para um objeto `Interpolation`, e quem processa o template decide o que fazer com isso. ([docs.python.org](https://docs.python.org/fr/3.14/builtins/stdtypes.html?utm_source=openai))
>
> ### Resumindo:
>
> - **f-string** → já monta a string final.
> - **t-string** → preserva a estrutura para processamento posterior. ([docs.python.org](https://docs.python.org/3/whatsnew/3.14.html?utm_source=openai))
>
> ## Propriedades importantes
>
> - São introduzidas no **Python 3.14**. ([docs.python.org](https://docs.python.org/3/whatsnew/3.14.html?utm_source=openai))
> - Usam prefixo `t` ou `T`. ([docs.python.org](https://docs.python.org/fr/3.14/builtins/stdtypes.html?utm_source=openai))
> - Resultam em `string.templatelib.Template`. ([docs.python.org](https://docs.python.org/3/whatsnew/3.14.html?utm_source=openai))
> - São **imutáveis**, embora possam referenciar objetos mutáveis como valores de interpolação. ([docs.python.org](https://docs.python.org/3/reference/expressions.html?highlight=walrus&utm_source=openai))
> - Cada avaliação de uma template string hoje produz um objeto diferente, segundo a implementação atual do CPython. ([docs.python.org](https://docs.python.org/3/reference/expressions.html?highlight=walrus&utm_source=openai))
>
> ## Um cuidado importante
>
> T-strings **não são** a mesma coisa que o antigo módulo `string.Template` com `$`-substituições. A documentação oficial deixa claro que são recursos diferentes. ([docs.python.org](https://docs.python.org/3/library/string.html?highlight=string+formatting&utm_source=openai))
>
> Se você quiser, eu também posso te mostrar:
> 1. a diferença entre **f-strings, t-strings e `string.Template`**; ou  
> 2. exemplos reais de **HTML seguro** e **SQL seguro** usando t-strings.
>
> Fontes:
> - https://docs.python.org/3/whatsnew/3.14.html?utm_source=openai
> - https://docs.python.org/fr/3.14/builtins/stdtypes.html?utm_source=openai
> - https://docs.python.org/3/reference/expressions.html?highlight=walrus&utm_source=openai
> - https://docs.python.org/3/library/string.html?highlight=string+formatting&utm_source=openai

## Pergunta com premissa falsa

O tutor corrige a premissa (`push` não existe em lista de Python) em vez de inventar o método, e mostra o que usar no lugar.

**Você:** Como uso lista.push() para adicionar um item numa lista?

**Chatbot:**

> Em Python, **lista.push() não existe**. Esse método é comum em outras linguagens, mas **listas de Python usam `append()`** para adicionar um item ao final.
>
> ### Exemplo
> ```python
> frutas = ["maçã", "banana"]
>
> frutas.append("laranja")
>
> print(frutas)
> ```
>
> ```text
> ['maçã', 'banana', 'laranja']
> ```
>
> ### O que usar no lugar
> - `append(item)` → adiciona **um item no final**
> - `extend(iterável)` → adiciona **vários itens**
> - `insert(indice, item)` → insere em uma posição específica
>
> ### Exemplos
> ```python
> numeros = [1, 2, 3]
>
> numeros.append(4)
> numeros.extend([5, 6])
> numeros.insert(0, 0)
>
> print(numeros)
> ```
>
> ```text
> [0, 1, 2, 3, 4, 5, 6]
> ```
>
> Se quiser, posso também te mostrar a diferença entre `append`, `extend` e `insert` com mais exemplos.

## Fora do escopo

Recusa curta e educada, trazendo a conversa de volta para Python, como pede o prompt.

**Você:** Qual a capital da França?

**Chatbot:**

> Desculpe, eu só respondo sobre Python. Se quiser, posso ajudar com dúvidas sobre a linguagem, sintaxe, módulos, tipagem, PEPs ou exemplos de código em Python.

## Caso de fronteira: o que mudou no Python 3.14

É a pergunta que ficou como limitação conhecida na ADR 0002. Nas duas rodadas da avaliação, o modelo não buscou e respondeu com certeza que a forma é inválida. Nesta execução ele buscou, e a resposta melhorou, mas ficou contraditória: diz que a forma "não é correta" e, no parágrafo seguinte, que o 3.14 a aceita sem `as`. O certo é: até o 3.13 é erro de sintaxe; a partir do 3.14 (PEP 758) é permitida sem `as`; com `as`, os parênteses continuam obrigatórios. O mesmo modelo, com a mesma pergunta, ora busca e ora não: é por isso que o caso pede outra solução que não uma regra de prompt.

**Você:** Posso escrever except ValueError, TypeError: para capturar duas exceções?

**Chatbot:**

> Sim — **mas não exatamente nesse formato**. O jeito correto, na maioria das versões do Python, é usar **parênteses**:
>
> ```python
> try:
>     ...
> except (ValueError, TypeError):
>     ...
> ```
>
> Isso captura **qualquer uma** dessas duas exceções. A documentação oficial diz que a expressão do `except` pode ser um tipo de exceção ou uma **tupla de tipos de exceção**. ([docs.python.org](https://docs.python.org/3/reference/compound_stmts.html?highlight=try&utm_source=openai))
>
> ### E `except ValueError, TypeError:`?
> Esse formato **não é a forma correta** para capturar duas exceções. Em Python moderno, sem parênteses, isso não representa uma tupla de exceções; a forma aceita é com parênteses. Além disso, a documentação recente indica que, a partir do Python 3.14, os parênteses podem até ser omitidos em alguns casos, mas **somente quando várias exceções são escritas diretamente no cabeçalho e não há `as`** — ainda assim, o formato tradicional e mais claro continua sendo com parênteses. ([docs.python.org](https://docs.python.org/3/reference/compound_stmts.html?highlight=try&utm_source=openai))
>
> ### Exemplo
> ```python
> try:
>     x = int("abc")
> except (ValueError, TypeError):
>     print("Deu ValueError ou TypeError")
> ```
>
> ```text
> Deu ValueError ou TypeError
> ```
>
> ### Observação útil
> Você também pode separar em dois `except` se quiser tratamento diferente para cada erro:
>
> ```python
> try:
>     ...
> except ValueError:
>     print("Valor inválido")
> except TypeError:
>     print("Tipo inválido")
> ```
>
> Se quiser, posso te mostrar **a diferença entre `except (A, B)` e dois `except` separados**.
>
> Fontes:
> - https://docs.python.org/3/reference/compound_stmts.html?highlight=try&utm_source=openai
