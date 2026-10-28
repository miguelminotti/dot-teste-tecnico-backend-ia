"""Configuração do chatbot, lida de variáveis de ambiente."""

import os
from collections.abc import Mapping
from dataclasses import dataclass

from chatbot.docs_search import MODELS_WITHOUT_DOCS_SEARCH

# Valores aceitos para ligar e desligar a busca; vazio fica com o padrão.
_FLAG_VALUES = {"true": True, "false": False}


@dataclass(frozen=True, slots=True, kw_only=True)
class Settings:
    """Configuração da aplicação; as variáveis e seus padrões estão documentados no `.env.example`.

    A chave da OpenAI não fica aqui: o cliente da OpenAI a lê sozinho de `OPENAI_API_KEY`, e guardá-la
    num objeto só aumentaria os lugares por onde ela pode vazar (um `repr` num log, por exemplo).
    """

    # Padrões escolhidos pelas avaliações (ADR 0002).
    model: str = "gpt-5.4-mini"
    # Busca na documentação oficial antes de responder (chatbot.docs_search).
    docs_search: bool = True

    @classmethod
    def from_env(cls, environ: Mapping[str, str] = os.environ) -> "Settings":
        # Sem a chave, o erro só apareceria na primeira pergunta, vindo de dentro da biblioteca da
        # OpenAI. Conferir na subida dá a mensagem certa antes de o usuário digitar qualquer coisa.
        if not environ.get("OPENAI_API_KEY", "").strip():
            raise ValueError("OPENAI_API_KEY não definida: copie o .env.example para .env e preencha a chave")
        model = environ.get("CHATBOT_MODEL", "").strip() or cls().model
        flag = environ.get("CHATBOT_DOCS_SEARCH", "").strip().casefold()
        if flag and flag not in _FLAG_VALUES:
            # Um valor desconhecido lido como desligado rodaria sem a busca sem ninguém perceber.
            raise ValueError(f"CHATBOT_DOCS_SEARCH deve ser true ou false, e não {flag!r}")
        docs_search = _FLAG_VALUES[flag] if flag else cls().docs_search
        if docs_search and model in MODELS_WITHOUT_DOCS_SEARCH:
            # Sem esta conferência, a API recusaria toda pergunta, e a CLI pediria para tentar de novo.
            raise ValueError(
                f"o {model} não aceita a busca na documentação; use CHATBOT_DOCS_SEARCH=false ou outro modelo"
            )
        return cls(model=model, docs_search=docs_search)
