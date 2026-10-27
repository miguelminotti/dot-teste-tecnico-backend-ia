# Questão 1 - API de biblioteca virtual

API para cadastrar e consultar livros (título, autor, data de publicação e resumo), com FastAPI e SQLite.

## Enunciado × status

| Requisito do enunciado | Status |
| --- | --- |
| Cadastro de livros com título, autor, data de publicação e resumo | entidade pronta, endpoint pendente |
| Consulta de livros por título ou autor | pendente |
| Implementação com Django, Flask ou FastAPI | FastAPI (pendente) |
| Endpoints claros e bem documentados | pendente |
| Armazenamento em SQLite | pendente |
| Testes unitários dos endpoints | pendente |

## Como rodar

Pré-requisito: [uv](https://docs.astral.sh/uv/). O uv baixa o Python 3.12 sozinho se ele não estiver instalado.

```bash
uv sync
```

Validação de estilo e de tipos:

```bash
uv run ruff check .
```

```bash
uv run ruff format --check .
```

```bash
uv run mypy
```

Testes:

```bash
uv run pytest
```

## Decisões

### Um repositório para a prova, um projeto uv por questão

As três questões ficam no mesmo repositório git, cada uma na sua pasta com `pyproject.toml` e `uv.lock` próprios. Um repositório só facilita a avaliação, com um link e um histórico. Projetos separados porque as dependências das questões não têm nada em comum: FastAPI aqui, LangChain e OpenAI na questão 2, FAISS e transformers (que trazem o torch) na questão 3. Juntar tudo num ambiente obrigaria quem roda a questão 1 a instalar o torch.

**Por que não um uv workspace:** o workspace resolve todas as questões num lockfile único, o que é útil quando os pacotes dependem uns dos outros. Aqui eles não dependem, então o workspace só acoplaria versões sem ganho.

### Layout `src` em vez de módulo solto

O projeto foi criado com `uv init --package`, que coloca o código em `src/library/` e o instala no ambiente como pacote. A alternativa (`uv init --app`) gera um `main.py` na raiz, mais simples, mas que deixa os testes importarem o código pelo diretório atual. Um teste pode passar localmente e o pacote estar quebrado. Com o `src`, testes, mypy e a aplicação importam o código do mesmo jeito.

### Python 3.12

Existem versões mais novas (3.13, 3.14), mas a 3.12 é a mais segura para as wheels de FAISS e torch da questão 3. A mesma versão nas três questões evita que cada uma rode num Python diferente, facilitando o uso.

### ruff com 120 colunas e conjunto enxuto de regras

O ruff faz lint e formatação numa ferramenta só, substituindo flake8, isort e black. Limite de 120 colunas. Regras ligadas:

| Código | Origem | Para que serve |
| --- | --- | --- |
| `E`, `W` | pycodestyle | estilo básico (PEP 8) |
| `F` | pyflakes | import não usado, nome indefinido |
| `I` | isort | ordem dos imports |
| `UP` | pyupgrade | sintaxe moderna para o Python alvo |
| `B` | flake8-bugbear | armadilhas comuns (argumento padrão mutável, por exemplo) |
| `SIM` | flake8-simplify | código que pode ser simplificado |

**Por que não `select = ["ALL"]`:** liga centenas de regras opinativas (docstring em toda função, que é particularmente desnecessário para o caso atual, proibição de `assert` nos testes) que gerariam ruído num projeto desse tamanho. O conjunto pode crescer se a necessidade surgir.

### mypy em modo `strict` desde o início

O `strict` exige anotação de tipos em todas as funções e recusa `Any` implícito, que ajuda bastante com a tipagem fraca da linguagem. Ele roda sobre `src/` e `tests/`.

### Código em inglês, documentação em português

Identificadores (classes, funções, campos e o contrato JSON da API) ficam em inglês; comentários, docstrings e este README, em português. A regra é não misturar idiomas dentro do código: `Book` com `title`, nunca `Livro` com `author`.

### DDD enxuto, com o domínio no centro

O que este sistema tem de interessante para mostrar é o domínio (o livro e suas regras), então o código segue Domain-Driven Design, mas na medida do tamanho do problema. Hoje existe só a camada de domínio:

```
src/library/
└── domain/
    ├── book.py               entidade Book e suas invariantes
    ├── publication_date.py   value object PublicationDate
    ├── clock.py              política de tempo (UTC)
    └── errors.py             erros de domínio
```

As próximas camadas entram quando forem necessárias, uma pasta cada: `application` (casos de uso, como cadastrar e buscar), `infrastructure` (repositório SQLite) e `api` (rotas FastAPI). A regra é que as dependências apontem para dentro: a API conhece o domínio, o domínio não conhece a API nem o banco. Isso deixa a porta aberta para trocar o SQLite por Postgres, ou expor o mesmo domínio por outra interface, sem tocar nas regras.

**Por que não mais granular:** value object só onde há regra e comportamento a proteger (`PublicationDate` sim, `Title` e `Author` não), e nada de agregados, eventos de domínio ou uma pasta por entidade. Com uma entidade e duas operações, essas peças seriam cerimônia sem regra para proteger: overengineering. Elas entram se o domínio crescer (empréstimos, exemplares, usuários), e a separação por camadas já dá o lugar onde encaixá-las.

### A entidade `Book`

- **dataclass, não pydantic.** O domínio fica em Python puro, sem depender de biblioteca de serialização. O pydantic entra na camada da API, nos schemas de entrada e saída, que convertem para a entidade.
- **Toda instância nasce válida.** As invariantes rodam no `__post_init__`: título, autor e resumo sem espaços nem caracteres invisíveis nas pontas e não vazios, data de cadastro com fuso. Uma violação levanta `InvalidBookError`, que a API vai traduzir em resposta 422.
- **Resumo obrigatório.** O enunciado lista o resumo junto dos outros campos sem marcá-lo como opcional.
- **Identidade por UUID gerado no domínio.** O livro nasce com `id` antes de tocar o banco, então não existe `id: int | None` espalhando checagens de `None` pelo código. O UUID também não expõe quantos livros existem, como faria `/livros/42`.
- **Igualdade pela identidade.** Dois livros com o mesmo título e autor continuam sendo livros diferentes se os ids forem diferentes. Por isso o `__eq__` gerado pela dataclass foi desligado e a comparação é só pelo `id`. Isso abre espaço para campos como editora e versão no futuro.

**Deixado de fora do domínio:** limite de tamanho para os textos. A diferença para a checagem de vazio está na origem da regra. Livro sem título, autor ou resumo não existe no domínio, e por isso essa regra mora na entidade e vale para qualquer porta de entrada (API, importação em lote, script). Já um teto como "título até 255 caracteres" não vem do negócio, porque nenhuma regra de biblioteca diz quanto um título pode medir. Ele seria um número arbitrário, e esse tipo de teto costuma nascer de duas preocupações de fora do domínio: o tipo de coluna do banco (`VARCHAR(255)`, no SQLite `TEXT` não tem limite) e a proteção contra payloads abusivos. As duas pertencem à borda, então o teto entra no schema da API, com o motivo explícito. Se aparecer uma regra de negócio de verdade, como um padrão de catálogo que limita o título, ela passa a ser invariante da entidade.

### O value object `PublicationDate`

Livros podem ser pré-cadastrados antes do lançamento, algo que editoras e bibliotecas usam com frequência para organizar o catálogo. Por isso a data de publicação aceita passado e futuro de propósito, e o domínio precisa responder "este livro já está publicado?".

**Por que não um campo `is_published` na entidade:** seria um segundo registro do mesmo fato, e os dois acabariam discordando (`is_published = true` com data futura, ou `false` com data passada). Com o value object, a data é a única fonte: `is_published(as_of)` deriva a resposta dela. Pelo mesmo motivo o campo deixou de se chamar `published_on`, que afirmaria um passado que nem sempre é verdade, e passou a ser `publication_date`.

**Por que value object e não um método no `Book`:** um método resolveria a dessincronia, mas o `PublicationDate` tem regra e comportamento próprios. Ele recusa `datetime` (a data de publicação é um dia, sem hora), é imutável e se compara por valor, e concentra o que é da data num lugar só. Também é onde caberia, no futuro, a precisão da data: muito livro antigo só tem o ano conhecido, e essa mudança ficaria dentro do value object, sem mexer na entidade nem na API.

**Por que `as_of` é obrigatório:** o value object não lê o relógio, recebe o dia de referência de quem chama. Qual "hoje" vale é decisão de negócio: às 22h de 27/10 em São Paulo o dia em UTC já é 28/10, e um lançamento de 28/10 apareceria publicado três horas antes. Quem conhece o fuso que importa (a camada de aplicação, normalmente o fuso da editora) decide. De quebra, o value object fica puro e os testes não precisam simular o relógio.

**Deixado de fora:** um enum de status (`ANNOUNCED`, `PUBLISHED`). Hoje só existem dois estados e os dois se derivam da data. O enum pode entrar quando aparecer um estado que a data não explica, como esgotado ou cancelado.

### Datas e fuso horário

O padrão do projeto é UTC para todo **instante** (data com hora). O cadastro do livro grava `created_at` em UTC, e o mesmo vale para o SQLite: o banco guarda instantes em UTC, nunca no horário local do servidor.

A **data de publicação** é exceção de propósito: ela é um dia do calendário, sem hora, e por isso `PublicationDate` guarda um `date`, não um `datetime`. Instantes levam o sufixo `_at` (`created_at`), para o nome dizer que ali há hora e fuso UTC. Se fosse um instante UTC, "10/03/2024 00:00 UTC" exibido em São Paulo apareceria como 09/03 às 21h, e o livro mudaria de dia conforme quem o consulta. É um bug comum em sistemas que tratam toda data como instante.

Duas regras sustentam o padrão, em `domain/clock.py`:

- `utc_now()` é o único ponto que lê o relógio. Ninguém chama `datetime.now()` sem fuso, que devolveria o horário local da máquina.
- `to_utc()` recusa instante sem fuso (naive) em vez de adivinhar o fuso dele, e converte qualquer instante com fuso para UTC.

**Clientes com outro relógio:** se a aplicação que consome a API trabalhar em America/Sao_Paulo, a conversão acontece na borda (entrada e saída da API), com um tradutor de fuso. O domínio e o banco continuam em UTC, e cada cliente vê o horário no seu fuso. Isso ainda não foi implementado porque nenhum cliente pede, mas o ponto de encaixe já está definido. No Windows, o `zoneinfo` do Python precisa do pacote `tzdata` para conhecer os fusos, detalhe que costuma aparecer só em produção.

### Testes: regras de negócio e casos de borda

Teste existe para impedir que uma mudança futura quebre um comportamento que não pode variar, principalmente os que custam dinheiro quando quebram: livro que some da busca, lançamento que aparece antes da hora, horário gravado com três horas de diferença. Por isso cada teste protege uma regra de negócio ou um caso de borda conhecido, e o comentário dentro dele diz qual estrago ele evita.

O que a suíte do domínio (`tests/domain/`) cobre:

| Arquivo | Regras protegidas |
| --- | --- |
| `test_clock.py` | relógio sempre em UTC; conversão que vira o dia (22h em São Paulo, 8h em Tóquio); recusa de instante sem fuso, inclusive o fuso que existe mas não informa offset |
| `test_publication_date.py` | o dia do lançamento já conta como publicado; data futura aceita (pré-cadastro); recusa de `datetime` como data de publicação e como dia de referência |
| `test_book.py` | título, autor e resumo em branco recusados (inclusive espaço não quebrável e caracteres invisíveis); espaços e invisíveis das pontas removidos, os do meio preservados; `created_at` sempre em UTC; identidade pelo `id` |

**Todo bug vira teste.** Quando um bug aparecer, o primeiro passo é um teste que o reproduz e falha; a correção vem depois e o teste fica na suíte para sempre. O caso fica registrado e protegido.

Bugs registrados até aqui:

**1. Texto só com caractere invisível era aceito**

- **Bug:** título, autor ou resumo só com espaço de largura zero (U+200B) ou BOM (U+FEFF) passava pela validação, e o livro entrava com título invisível. Com o caractere nas pontas, "Machado de Assis" e "Machado de Assis" + U+200B viravam autores diferentes na busca.
- **Como apareceu:** escrevendo a suíte do domínio. O `str.strip()` só remove o que o Python considera espaço, e esses caracteres são da categoria Unicode "Cf" (formatação). Chegam colados de sites, PDFs e planilhas.
- **Testes que o protegem:** `test_rejects_blank_required_text` (casos `largura-zero`, `bom` e `misturado`) e `test_strips_invisible_characters_from_the_edges`.
- **Correção:** `_strip_invisible`, em `book.py`, remove espaços e caracteres "Cf" só das pontas. No meio do texto eles ficam, porque lá compõem emojis e a escrita de idiomas como persa e hindi. `test_keeps_invisible_characters_inside_the_text` impede que a correção vá longe demais.

**Como saber se os testes protegem de verdade:** cada regra do domínio foi quebrada de propósito, uma por vez (trocar `<=` por `<` no `is_published`, tirar o `strip`, tirar a checagem de offset, trocar `utc_now()` por `datetime.now()`, desligar a igualdade por `id`, aceitar `datetime` como data de publicação, pular a conversão do `created_at`), e em todas a suíte falhou. É necessário garantir que um teste fica vermelho se sua regra de proteção for quebrada, seguindo os padrões de RED -> GREEN.

**Fusos com offset fixo:** os testes usam `timezone(timedelta(hours=-3))` em vez de `ZoneInfo("America/Sao_Paulo")`. O que está em teste é a conversão, não a base de fusos do sistema, que no Windows depende do pacote `tzdata` e muda com regras de horário de verão.

**Deixado de fora:** testes da mecânica da dataclass (imutabilidade do `PublicationDate`, `repr`, igualdade por valor). Eles testariam o Python, não uma regra nossa; entram se alguma dessas propriedades passar a sustentar uma regra de negócio.
