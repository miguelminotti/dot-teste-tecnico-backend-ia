# ADR 0005: `PublicationDate` como fonte única do estado de publicação

- **Status:** Aceita
- **Data:** 2026-10-27

## Contexto

Editoras e bibliotecas pré-cadastram livros antes do lançamento para organizar o catálogo. Então a data de publicação pode estar no futuro, e o sistema precisa responder "este livro já está publicado?". Guardar essa resposta num campo próprio (`is_published`) cria dois registros do mesmo fato, que acabam discordando: `true` com data futura, ou `false` com data passada. Um campo chamado `published_on` também afirmaria um passado que nem sempre é verdade.

## Decisão

- A data de publicação é o value object `PublicationDate`, imutável e comparado por valor, guardado no campo `Book.publication_date`.
- Data passada e futura são aceitas.
- `PublicationDate` recusa `datetime`: a data de publicação é um dia, sem hora (ver [ADR 0002](0002-instantes-em-utc-datas-sem-fuso.md)).
- O estado de publicação é derivado, nunca guardado: `is_published(as_of: date)`, em que o próprio dia do lançamento já conta como publicado.
- `as_of` é obrigatório e é uma `date`. O value object não lê o relógio, porque qual "hoje" vale é decisão de negócio: às 22h de 27/10 em São Paulo, o dia em UTC já é 28/10, e um lançamento de 28/10 apareceria publicado três horas antes. Quem conhece o fuso que importa (a camada de aplicação, normalmente o fuso da editora) decide.

## Alternativas consideradas

- **Campo `is_published` na entidade:** dessincronia entre flag e data.
- **Método `is_published` no `Book`, com `date` simples:** resolveria a dessincronia, mas a regra "dia sem hora" e o comportamento da data ficariam espalhados na entidade.
- **Enum de status (`ANNOUNCED`, `PUBLISHED`):** com dois estados derivados da data, seria redundante. Entra quando aparecer um estado que a data não explica, como esgotado ou cancelado.
- **Bloquear data futura:** impediria o pré-cadastro.

## Consequências

- O schema da API e o repositório convertem `PublicationDate` de e para `date`; o JSON continua mostrando uma data simples.
- A camada de aplicação precisa decidir o dia de referência ao responder se um livro está publicado.
- Precisão parcial (só o ano conhecido, comum em livros antigos) cabe dentro do value object, sem mexer na entidade nem na API.
