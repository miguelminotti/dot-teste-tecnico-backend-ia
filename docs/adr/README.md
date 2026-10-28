# ADRs do repositório

Architecture Decision Records: decisões tomadas na concepção do código que são difíceis de reverter, porque definem regras para um contexto. Servem para revisão e para que pessoas e agentes entendam por que o projeto é como é sem reconstruir o raciocínio a partir do código.

Aqui ficam as decisões que valem para todas as questões. As de uma questão só ficam em `questao-N/docs/adr/` (ver [ADR 0001](0001-monorepo-com-projeto-uv-por-questao.md)). Convenções (idioma, lint, tipagem) não são ADR e ficam no [README da raiz](../../README.md).

| ADR | Decisão | Status |
| --- | --- | --- |
| [0001](0001-monorepo-com-projeto-uv-por-questao.md) | Um repositório para a prova, um projeto uv por questão, todos em Python 3.12 | Aceita |

## Formato

Um arquivo por decisão, `NNNN-titulo-curto.md`, numerado em sequência. Cada ADR tem status, data, contexto, decisão, alternativas consideradas e consequências.

Uma ADR registra o porquê e as alternativas descartadas, não o que o código já mostra: nomes de arquivo, de função, de variável de ambiente e valores de configuração ficam no código e no README, onde não envelhecem separados dele. Se uma decisão não tem alternativa que alguém defenderia de verdade, ela não precisa de ADR.

ADR aceita não é editada para mudar a decisão. Se a decisão mudar, uma ADR nova a substitui, e a antiga passa a ter status "Substituída pela ADR NNNN". Assim o histórico do porquê fica preservado.
