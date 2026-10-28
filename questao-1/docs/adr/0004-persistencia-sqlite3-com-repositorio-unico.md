# ADR 0004: Persistência com `sqlite3` da stdlib, num repositório único

- **Status:** Aceita
- **Data:** 2026-10-27

## Contexto

O enunciado pede SQLite. O sistema tem uma tabela, uma escrita (cadastro) e uma leitura (busca). A política de datas ([ADR 0003](0003-datas-e-estado-de-publicacao.md)) exige controle de como datas são gravadas.

## Decisão

- **Porta no domínio, implementação na infraestrutura.** O domínio define o contrato de persistência; o repositório SQLite o implementa, e a aplicação depende só do contrato.
- **`sqlite3` da biblioteca padrão, sem ORM.** SQL explícito e conversão manual entre linha e entidade.
- **Um repositório para leitura e escrita**, sobre o mesmo banco.
- **O banco repete as regras de formato:** tabela `STRICT`, que recusa valor de tipo errado em vez de convertê-lo, e `CHECK`s com a política de datas, para valerem também para quem gravar sem passar pelo repositório.
- **Conexão injetada.** O repositório recebe a conexão pronta; quem a abre e fecha (a API, uma por requisição) controla o ciclo de vida. Cada cadastro é uma transação própria.
- **Erros do banco não vazam.** Chave primária duplicada vira erro de domínio; qualquer outra violação de integridade é bug e estoura como está.
- **A busca é sempre paginada:** o contrato exige o tamanho da página, então nenhuma chamada devolve o acervo inteiro.

## Alternativas consideradas

- **SQLAlchemy 2.0:** abstrai o dialeto e abre caminho para Alembic e Postgres, mas é uma dependência e uma camada de mapeamento a mais para uma tabela. Trocar de banco hoje reescreve só o repositório, que é o que a porta isola.
- **SQLModel:** idiomático com FastAPI, mas tende a fundir tabela, schema da API e entidade num modelo só, o que contraria o domínio puro ([ADR 0002](0002-entidade-valida-com-identidade-propria.md)).
- **CQRS (repositórios ou modelos separados para leitura e escrita):** com um endpoint de cada, o mesmo repositório atende os dois. Separar entra se leitura e escrita passarem a ter necessidades diferentes (volume, formato, banco).
- **Repositório falso para os testes:** desnecessário; o SQLite em memória é o banco real e serve aos testes.
- **Migrations (Alembic):** sem dados em produção e com uma tabela, não há o que migrar. Entra na primeira mudança de schema.

## Consequências

- Nenhuma dependência nova.
- Os testes da infraestrutura rodam contra SQLite real, sem simular o banco.
- Uma operação que precise de várias escritas atômicas vai exigir controle de transação acima do repositório (unit of work), hoje deixado de fora.
- **Limitação conhecida:** a leitura reidrata o livro pelo construtor, então uma linha gravada sem passar pelo repositório que viole uma regra do livro (título só com espaços, por exemplo) faz a busca levantar um erro de domínio, e a API responde 422 a uma leitura, quando o certo seria 500. Fica assim porque só uma escrita por fora do repositório produz essa linha, e os `CHECK`s do banco já barram as datas fora da política.
