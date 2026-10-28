# ADR 0002: Entidade válida por construção, com identidade própria

- **Status:** Aceita
- **Data:** 2026-10-27

## Contexto

Uma entidade precisa de identidade estável. Se o id vem do banco (autoincremento), o livro existe sem id até ser salvo, o tipo vira "inteiro ou nada" e as checagens de nulo se espalham. Ids sequenciais na URL também revelam quantos livros existem e permitem varrer o acervo.

O livro pode entrar no sistema por mais de uma porta: a API hoje, e no futuro importação em lote ou scripts. Se a validação morar só no schema da API, outra porta cria um livro inválido. Ao mesmo tempo, nem toda validação é regra de negócio: limite de tamanho, por exemplo, vem da proteção contra abuso.

## Decisão

- O livro nasce com um UUID gerado no próprio domínio, antes de tocar o banco, e se compara só pela identidade: dois livros com os mesmos dados e ids diferentes são livros diferentes.
- O domínio é Python puro, sem pydantic.
- As invariantes rodam na construção, então não existe livro inválido em memória: título, autor e resumo precisam ter conteúdo visível, e o instante do cadastro precisa ter fuso. Ao ler do banco, a entidade é reconstruída pelo mesmo caminho, e as invariantes rodam de novo.
- Violação levanta um erro de domínio próprio, que diz o campo violado. A API o traduz em HTTP.
- O critério para uma validação morar no domínio é a origem da regra: se vem do negócio (livro sem título não existe), é invariante da entidade; se vem de fora do negócio (tamanho máximo de payload), fica na borda, com o motivo explícito.

## Alternativas consideradas

- **Autoincremento do banco:** mais simples e legível na URL, mas com id opcional na entidade e o volume do acervo exposto.
- **Igualdade por atributos (o padrão da dataclass):** duas edições com mesmo título e autor se fundiriam numa deduplicação.
- **Pydantic no domínio:** acopla as regras a uma biblioteca de serialização, e a validação passa a depender de como o objeto foi construído.
- **Limite de tamanho dos textos na entidade:** seria um número arbitrário; nenhuma regra de biblioteca diz quanto um título pode medir.

## Consequências

- Qualquer porta de entrada recebe as mesmas garantias sem repetir validação.
- Testes montam livros com id fixo para simular o mesmo registro lido duas vezes.
- Campos como editora e edição cabem no futuro: duas edições do mesmo título e autor já são livros distintos.
- Se aparecer uma regra de tamanho vinda do negócio (padrão de catálogo, por exemplo), ela passa a ser invariante da entidade.
