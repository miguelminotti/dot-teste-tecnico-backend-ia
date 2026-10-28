"""Configuração do chatbot, lida de variáveis de ambiente."""

import os
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class Settings:
    """Configuração da aplicação; as variáveis e seus padrões estão documentados no `.env.example`.

    A chave da OpenAI não fica aqui: o cliente da OpenAI a lê sozinho de `OPENAI_API_KEY`, e guardá-la
    num objeto só aumentaria os lugares por onde ela pode vazar (um `repr` num log, por exemplo).
    """

    model: str = "gpt-4.1-mini"

    @classmethod
    def from_env(cls, environ: Mapping[str, str] = os.environ) -> "Settings":
        # Sem a chave, o erro só apareceria na primeira pergunta, vindo de dentro da biblioteca da
        # OpenAI. Conferir na subida dá a mensagem certa antes de o usuário digitar qualquer coisa.
        if not environ.get("OPENAI_API_KEY", "").strip():
            raise ValueError("OPENAI_API_KEY não definida: copie o .env.example para .env e preencha a chave")
        model = environ.get("CHATBOT_MODEL", "").strip() or cls().model
        return cls(model=model)
