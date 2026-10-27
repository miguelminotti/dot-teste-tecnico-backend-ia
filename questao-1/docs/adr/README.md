# ADRs da questão 1

Decisões de arquitetura da API de biblioteca. As que valem para o repositório inteiro (monorepo, Python 3.12, idioma do código, ruff e mypy) estão em [`docs/adr/`](../../../docs/adr/README.md) na raiz, junto com o formato adotado.

| ADR | Decisão | Status |
| --- | --- | --- |
| [0001](0001-ddd-enxuto-em-camadas.md) | DDD enxuto, em camadas com dependências para dentro | Aceita |
| [0002](0002-instantes-em-utc-datas-sem-fuso.md) | Instantes em UTC, datas de calendário sem fuso | Aceita |
| [0003](0003-identidade-por-uuid-do-dominio.md) | Identidade por UUID gerado no domínio | Aceita |
| [0004](0004-entidade-valida-por-construcao.md) | Entidade válida por construção; regra de negócio no domínio, proteção na borda | Aceita |
| [0005](0005-publication-date-como-fonte-unica.md) | `PublicationDate` como fonte única do estado de publicação | Aceita |
| [0006](0006-testes-protegem-regras-de-negocio.md) | Testes protegem regras de negócio; todo bug vira teste | Aceita |
| [0007](0007-persistencia-sqlite3-com-repositorio-unico.md) | Persistência com `sqlite3` da stdlib, num repositório único | Aceita |
| [0008](0008-busca-sem-caixa-e-sem-acento.md) | Busca parcial, sem diferenciar maiúsculas nem acentos | Aceita |
