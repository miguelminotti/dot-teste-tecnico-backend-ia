# ADR 0004: Entidade válida por construção; regra de negócio no domínio, proteção na borda

- **Status:** Aceita
- **Data:** 2026-10-27

## Contexto

O livro pode entrar no sistema por mais de uma porta: a API hoje, e no futuro importação em lote ou scripts. Se a validação morar só no schema da API, outra porta pode criar um livro inválido. Ao mesmo tempo, nem toda validação é regra de negócio: limite de tamanho, por exemplo, costuma vir do banco ou da proteção contra abuso.

## Decisão

- O domínio é Python puro: `Book` e `PublicationDate` são dataclasses, sem pydantic. O pydantic fica nos schemas da API, que convertem de e para a entidade.
- As invariantes rodam no `__post_init__`, então não existe instância inválida: título, autor e resumo obrigatórios, sem espaços nem caracteres invisíveis (categoria Unicode "Cf") nas pontas; `created_at` com fuso, normalizado para UTC.
- Violação levanta erro de domínio próprio, filho de `DomainError` (`InvalidBookError`, `InvalidPublicationDateError`, `NotProvidedTimezoneError`). O nome evita `ValidationError`, que é do pydantic e vai conviver com eles na API. A API traduz `DomainError` em 422.
- O critério para uma validação morar no domínio é a origem da regra: se vem do negócio (livro sem título não existe), é invariante da entidade; se vem de fora do negócio (tipo de coluna do banco, tamanho máximo de payload), fica na borda, com o motivo explícito.

## Alternativas consideradas

- **Pydantic no domínio:** acopla as regras a uma biblioteca de serialização, e a validação passa a depender de como o objeto foi construído.
- **Limite de tamanho dos textos na entidade:** seria um número arbitrário; nenhuma regra de biblioteca diz quanto um título pode medir. Vai para o schema da API.

## Consequências

- Qualquer porta de entrada recebe as mesmas garantias sem repetir validação.
- A API precisa mapear `DomainError` para resposta HTTP.
- Se aparecer uma regra de tamanho vinda do negócio (padrão de catálogo, por exemplo), ela passa a ser invariante da entidade.
