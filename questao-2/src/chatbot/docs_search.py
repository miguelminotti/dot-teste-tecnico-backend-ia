"""Busca na documentação oficial, pela ferramenta de busca web hospedada da OpenAI."""

from typing import Any

# Domínios onde a busca pode ir; os subdomínios entram junto. Só documentação mantida pelo próprio
# projeto: hospedagens abertas (readthedocs.io inteiro, github.com, pypi.org, blogs) ficam de fora,
# porque qualquer pessoa publica nelas, e uma página com instruções escondidas para o modelo entraria
# na resposta. Uma biblioteca nova entra aqui quando uma avaliação mostrar uma pergunta sobre ela.
DOCS_DOMAINS = (
    "docs.python.org",
    "peps.python.org",
    "packaging.python.org",
    "typing.python.org",
    "docs.pydantic.dev",
)

# O filtro de domínios não é aceito em todo modelo: o gpt-4.1-mini recusa a chamada (400), e o
# gpt-5.4-mini aceita. A busca roda nos servidores da OpenAI, dentro da mesma chamada ao modelo.
WEB_SEARCH_TOOL: dict[str, Any] = {"type": "web_search", "filters": {"allowed_domains": list(DOCS_DOMAINS)}}
