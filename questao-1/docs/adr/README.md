# ADRs da questão 1

Decisões de arquitetura da API de biblioteca. As que valem para o repositório inteiro estão em [`docs/adr/`](../../../docs/adr/README.md) na raiz, junto com o formato adotado.

| ADR | Decisão | Status |
| --- | --- | --- |
| [0001](0001-ddd-enxuto-em-camadas.md) | DDD enxuto, em camadas, com a aplicação como única porta da API | Aceita |
| [0002](0002-entidade-valida-com-identidade-propria.md) | Entidade válida por construção, com identidade própria | Aceita |
| [0003](0003-datas-e-estado-de-publicacao.md) | Instantes em UTC, data de publicação como dia, publicação derivada | Aceita |
| [0004](0004-persistencia-sqlite3-com-repositorio-unico.md) | Persistência com `sqlite3` da stdlib, num repositório único | Aceita |
| [0005](0005-busca-sem-caixa-e-sem-acento.md) | Busca parcial, sem diferenciar maiúsculas nem acentos | Aceita |
| [0006](0006-contrato-http-paginado-e-validacao-na-borda.md) | Contrato HTTP com paginação obrigatória e validação estrita na borda | Aceita |
| [0007](0007-rate-limiting-proprio-em-memoria.md) | Rate limiting próprio, por IP, em janela fixa e em memória | Aceita |
