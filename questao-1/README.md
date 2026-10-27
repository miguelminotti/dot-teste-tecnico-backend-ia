# Questão 1 - API de biblioteca virtual

API para cadastrar e consultar livros (título, autor, data de publicação e resumo), com FastAPI e SQLite.

## Enunciado × status

| Requisito do enunciado | Status |
| --- | --- |
| Cadastro de livros com título, autor, data de publicação e resumo | entidade pronta, endpoint pendente |
| Consulta de livros por título ou autor | pendente |
| Implementação com Django, Flask ou FastAPI | FastAPI (pendente) |
| Endpoints claros e bem documentados | pendente |
| Armazenamento em SQLite | repositório pronto e testado |
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

## Estrutura

```
src/library/
├── domain/
│   ├── book.py                      entidade Book e suas invariantes
│   ├── publication_date.py          value object PublicationDate
│   ├── repository.py                porta BookRepository (o que o domínio precisa do banco)
│   ├── clock.py                     política de tempo (UTC)
│   └── errors.py                    erros de domínio
└── infrastructure/
    ├── database.py                  conexão e schema do SQLite
    └── sqlite_book_repository.py    SqliteBookRepository, implementação da porta
tests/
├── conftest.py                      fixture make_book, compartilhada entre as suítes
├── domain/                          testes unitários do domínio
└── infrastructure/                  testes do repositório contra SQLite real
docs/adr/                            decisões de arquitetura desta questão
```

As camadas `application` e `api` entram quando forem usadas ([ADR 0001](docs/adr/0001-ddd-enxuto-em-camadas.md)).

## Decisões

Cada decisão de arquitetura tem uma ADR com contexto, alternativas descartadas e consequências. Aqui fica só o resumo.

### Do repositório ([`../docs/adr/`](../docs/adr/README.md))

- **Um repositório, um projeto uv por questão.** As dependências das questões não se sobrepõem, e a questão 3 traz o torch. Uv workspace descartado por acoplar versões sem ganho. [ADR 0001](../docs/adr/0001-monorepo-com-projeto-uv-por-questao.md)
- **Python 3.12.** Versão mais segura para as wheels de FAISS e torch da questão 3, igual nas três questões. [ADR 0002](../docs/adr/0002-python-3-12.md)
- **Código em inglês, documentação em português.** Sem misturar idiomas dentro do código. [ADR 0003](../docs/adr/0003-codigo-em-ingles-documentacao-em-portugues.md)
- **ruff (120 colunas, regras enxutas) e mypy strict sobre `src/` e `tests/`, com layout `src`.** [ADR 0004](../docs/adr/0004-qualidade-ruff-e-mypy-strict.md)

### Desta questão ([`docs/adr/`](docs/adr/README.md))

- **DDD enxuto.** Camadas com dependências apontando para dentro; o domínio não conhece banco nem framework. Value object só onde há regra a proteger, sem agregados ou eventos enquanto o domínio for uma entidade e duas operações. [ADR 0001](docs/adr/0001-ddd-enxuto-em-camadas.md)
- **Instantes em UTC, datas de calendário sem fuso.** `created_at` é UTC no domínio e no banco; a data de publicação é `date` e não muda de dia conforme o fuso de quem consulta. Clientes em outro fuso são atendidos na borda. [ADR 0002](docs/adr/0002-instantes-em-utc-datas-sem-fuso.md)
- **Identidade por UUID gerado no domínio.** O livro nasce com `id`, sem `id: int | None`, e se compara só pelo `id`. [ADR 0003](docs/adr/0003-identidade-por-uuid-do-dominio.md)
- **Entidade válida por construção.** Invariantes no `__post_init__`, erros de domínio próprios. Regra que vem do negócio fica no domínio; proteção técnica, como limite de tamanho dos textos, fica no schema da API. [ADR 0004](docs/adr/0004-entidade-valida-por-construcao.md)
- **`PublicationDate` como fonte única do estado de publicação.** Aceita data futura (pré-cadastro) e deriva `is_published(as_of)` em vez de guardar uma flag; o dia de referência vem de quem chama. [ADR 0005](docs/adr/0005-publication-date-como-fonte-unica.md)
- **Testes protegem regras de negócio; todo bug vira teste.** [ADR 0006](docs/adr/0006-testes-protegem-regras-de-negocio.md)
- **Persistência com `sqlite3` da stdlib, num repositório único.** Porta no domínio, implementação na infraestrutura, SQL explícito e sem ORM. Leitura e escrita no mesmo repositório: CQRS seria exagero para um endpoint de cada. Tabela `STRICT` com `CHECK`s que repetem a política de datas no banco. [ADR 0007](docs/adr/0007-persistencia-sqlite3-com-repositorio-unico.md)
- **Busca parcial, sem diferenciar maiúsculas nem acentos.** "jose" acha "José de Alencar"; `%` e `_` digitados são texto, não curinga. [ADR 0008](docs/adr/0008-busca-sem-caixa-e-sem-acento.md)

Decisão de produto, fora das ADRs: o **resumo é obrigatório**, porque o enunciado o lista junto dos outros campos sem marcá-lo como opcional.

## Testes

O que cada suíte cobre:

| Arquivo | Regras protegidas |
| --- | --- |
| `test_clock.py` | relógio sempre em UTC; conversão que vira o dia (22h em São Paulo, 8h em Tóquio); recusa de instante sem fuso, inclusive o fuso que existe mas não informa offset |
| `test_publication_date.py` | o dia do lançamento já conta como publicado; data futura aceita (pré-cadastro); recusa de `datetime` como data de publicação e como dia de referência |
| `test_book.py` | título, autor e resumo em branco recusados (inclusive espaço não quebrável e caracteres invisíveis); espaços e invisíveis das pontas removidos, os do meio preservados; `created_at` sempre em UTC; identidade pelo `id` |
| `test_sqlite_book_repository.py` | cadastro sobrevive ao fechar a conexão (commit); ida e volta preserva todos os campos, inclusive data futura e horário de São Paulo; datas gravadas em UTC de largura fixa e dia puro; `id` duplicado vira erro de domínio sem sobrescrever o original; erro não deixa transação aberta; oito cadastros simultâneos do mesmo livro gravam um só; recriar o schema não apaga o acervo; banco recusa datas fora da política; busca sem caixa e acento, com `%`, `_` e `\` como texto, filtros combinados com E, ordem alfabética e desempate por `id` |

Os testes da infraestrutura rodam contra SQLite real, sem fake: em memória quando basta uma conexão, num arquivo temporário quando precisam de mais de uma (persistência e concorrência).

**Os testes protegem de verdade:** é necessário garantir que um teste fica vermelho se sua regra for quebrada, seguindo os padrões de RED -> GREEN. Cada regra foi quebrada de propósito, uma por vez, e em todas a suíte falhou:

- **Domínio:** trocar `<=` por `<` no `is_published`, tirar o `strip`, tirar a checagem de offset, trocar `utc_now()` por `datetime.now()`, desligar a igualdade por `id`, aceitar `datetime` como data de publicação, pular a conversão do `created_at`.
- **Repositório:** tirar o commit, trocar por `INSERT OR REPLACE`, não escapar `%`, buscar sem normalizar, ordenar pela coluna original, tirar o desempate por `id`, gravar `created_at` sem largura fixa, combinar filtros com OU, recriar a tabela no `create_schema`, tirar o `CHECK` de UTC, e trocar a chave primária por um "já existe?" antes do insert (check-then-act). Este último depende de corrida entre threads, então foi rodado 20 vezes: a suíte falhou nas 20.

**Deixado de fora:** teste de N+1. A busca é uma consulta só, e a reidratação do `Book` não consulta o banco; com uma tabela e nenhuma relação, não existe N+1 possível. O teste entra junto com a primeira relação (autor como tabela própria, por exemplo), contando as consultas com `connection.set_trace_callback`.

### Bugs registrados

Todo bug vira um teste que o reproduz antes da correção ([ADR 0006](docs/adr/0006-testes-protegem-regras-de-negocio.md)).

**1. Texto só com caractere invisível era aceito**

- **Bug:** título, autor ou resumo só com espaço de largura zero (U+200B) ou BOM (U+FEFF) passava pela validação, e o livro entrava com título invisível. Com o caractere nas pontas, "Machado de Assis" e "Machado de Assis" + U+200B viravam autores diferentes na busca.
- **Como apareceu:** escrevendo a suíte do domínio. O `str.strip()` só remove o que o Python considera espaço, e esses caracteres são da categoria Unicode "Cf" (formatação). Chegam colados de sites, PDFs e planilhas.
- **Testes que o protegem:** `test_rejects_blank_required_text` (casos `largura-zero`, `bom` e `misturado`) e `test_strips_invisible_characters_from_the_edges`.
- **Correção:** `_strip_invisible`, em `book.py`, remove espaços e caracteres "Cf" só das pontas. No meio do texto eles ficam, porque lá compõem emojis e a escrita de idiomas como persa e hindi. `test_keeps_invisible_characters_inside_the_text` impede que a correção vá longe demais.
