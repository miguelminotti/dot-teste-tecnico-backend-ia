# ADRs do repositório

Architecture Decision Records: decisões tomadas na concepção do código que são difíceis de reverter, porque definem regras para um contexto. Servem para revisão e para que pessoas e agentes entendam os padrões do projeto sem ler o código.

Aqui ficam as decisões que valem para todas as questões. As de uma questão só ficam em `questao-N/docs/adr/` (ver [ADR 0001](0001-monorepo-com-projeto-uv-por-questao.md)).

| ADR | Decisão | Status |
| --- | --- | --- |
| [0001](0001-monorepo-com-projeto-uv-por-questao.md) | Um repositório para a prova, um projeto uv por questão | Aceita |
| [0002](0002-python-3-12.md) | Python 3.12 em todas as questões | Aceita |
| [0003](0003-codigo-em-ingles-documentacao-em-portugues.md) | Código em inglês, documentação em português | Aceita |
| [0004](0004-qualidade-ruff-e-mypy-strict.md) | Qualidade com ruff e mypy strict, sobre código e testes | Aceita |

## Formato

Um arquivo por decisão, `NNNN-titulo-curto.md`, numerado em sequência e nunca renumerado. Cada ADR tem status, data, contexto, decisão, alternativas consideradas e consequências.

ADR aceita não é editada para mudar a decisão. Se a decisão mudar, uma ADR nova a substitui, e a antiga passa a ter status "Substituída pela ADR NNNN". Assim o histórico do porquê fica preservado.
