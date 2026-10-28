# ADR 0003: Instantes em UTC, data de publicação como dia, publicação derivada

- **Status:** Aceita
- **Data:** 2026-10-27

## Contexto

Datas são uma fonte comum de bugs silenciosos: horário gravado no fuso local do servidor, instante sem fuso interpretado de jeitos diferentes em cada máquina, e datas que mudam de dia conforme quem consulta. O livro tem dois tipos de data, de naturezas diferentes:

- **Instante:** um ponto no tempo, com hora (quando o livro foi cadastrado).
- **Dia do calendário:** um dia, sem hora (a data de publicação).

O enunciado pede só a data de publicação. Esta solução vai um passo além e responde se o livro já foi publicado, porque editoras e bibliotecas pré-cadastram livros antes do lançamento. É uma extensão, e por isso fica isolada: se o negócio não quiser esse conceito, ele sai sem tocar o resto.

## Decisão

- **Instantes** têm fuso e ficam em UTC, no domínio e no banco. Um único ponto do projeto lê o relógio. Instante sem fuso é recusado, em vez de o sistema adivinhar de onde ele é.
- **A data de publicação** é um dia, sem hora, e nunca passa por conversão de fuso. É um value object que recusa hora e aceita datas passadas e futuras (pré-cadastro).
- **O estado de publicação é derivado, nunca guardado:** o value object responde se o livro está publicado num dia de referência, e o próprio dia do lançamento já conta.
- **Qual é o "hoje" é decisão de negócio**, então não é lido dentro do value object. A aplicação decide, no fuso configurado da biblioteca, e usa um único "hoje" para todos os livros de uma resposta.
- A API devolve instantes em UTC. Se um cliente precisar deles em outro fuso, a conversão acontece na borda, nunca no domínio ou no banco; ela não foi implementada porque nenhum cliente a pede.

## Alternativas consideradas

- **Data de publicação como instante UTC:** "10/03/2024 00:00 UTC" exibido em São Paulo vira 09/03 às 21h, e o livro muda de dia conforme quem consulta.
- **Horário local do servidor:** muda se o servidor mudar de região, e o horário de verão gera horas repetidas ou inexistentes.
- **Flag de publicado guardada no livro:** dois registros do mesmo fato, que acabam discordando (publicado com data futura, ou o contrário).
- **Estado calculado na entidade, com a data como `date` simples:** resolveria a dessincronia, mas a regra "dia sem hora" e o comportamento da data ficariam espalhados na entidade.
- **Enum de status (anunciado, publicado):** com dois estados derivados da data, seria redundante. Entra quando aparecer um estado que a data não explica, como esgotado ou cancelado.
- **"Hoje" em UTC:** às 22h de 27/10 em São Paulo o dia em UTC já é 28/10, e um lançamento de 28/10 apareceria publicado três horas antes.
- **Bloquear data futura:** impediria o pré-cadastro.

## Consequências

- O SQLite não tem tipo de data: instantes são gravados como texto ISO 8601 com o offset explícito, e o banco recusa os que fogem da política. O adaptador padrão de datas do `sqlite3` está deprecado desde o Python 3.12 e grava sem fuso, então não é usado.
- O fuso da biblioteca exige a base de fusos, que o Windows não traz; por isso o `tzdata` é dependência.
- Precisão parcial (só o ano conhecido, comum em livros antigos) cabe dentro do value object, sem mexer na entidade nem na API.
- Tirar o estado de publicação mexe só no value object, na aplicação e no DTO de saída.
