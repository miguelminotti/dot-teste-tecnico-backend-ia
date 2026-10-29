from collections.abc import Callable, Sequence
from typing import Any

import httpx2
import openai
import pytest
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from pydantic import Field

from chatbot.docs_search import DOCS_DOMAINS
from chatbot.tutor import SYSTEM_PROMPT, AnswerUnavailableError, OpenAIAccountError, Tutor


class RecordingChatModel(BaseChatModel):
    """Modelo falso: guarda as mensagens de cada chamada e responde "resposta N" na chamada N.

    Os modelos falsos do `langchain-core` (`FakeListChatModel`, `GenericFakeChatModel` e afins)
    respondem, mas descartam as mensagens que recebem, e o que estes testes conferem é justamente o
    que o `Tutor` envia. Nenhum deles falha numa chamada escolhida fora do streaming, e o `Tutor` usa
    `invoke`.
    """

    calls: list[list[BaseMessage]] = Field(default_factory=list)
    # Número da chamada (a partir de 1) que falha, para simular a API fora do ar, e o erro levantado.
    fail_on_call: int | None = None
    failure: Any = Field(default_factory=lambda: RuntimeError("falha simulada"))
    # Conteúdo da resposta em blocos, como a Responses API devolve; sem ele, responde "resposta N".
    reply_blocks: list[str | dict[Any, Any]] | None = None
    # Ferramentas que o `Tutor` ligou ao modelo.
    tools: list[Any] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "recording"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        self.calls.append(list(messages))
        if len(self.calls) == self.fail_on_call:
            raise self.failure
        content = self.reply_blocks if self.reply_blocks is not None else f"resposta {len(self.calls)}"
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content))])

    def bind_tools(
        self,
        tools: Sequence[dict[str, Any] | type | Callable[..., Any] | BaseTool],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, AIMessage]:
        self.tools = list(tools)
        return self


def _sent(messages: list[BaseMessage]) -> list[tuple[str, str | list[Any]]]:
    """O que de fato vai ao modelo em cada mensagem: o papel e o texto."""
    return [(message.type, message.content) for message in messages]


def test_follow_up_question_reaches_the_model_with_the_previous_turns() -> None:
    # Sem o histórico, "e como removo um item dela?" chega ao modelo sem saber de que lista se trata,
    # e o "Quer que eu explique mais?" do fim das respostas não teria como ser aceito.
    model = RecordingChatModel()
    tutor = Tutor(model)

    tutor.answer("Como criar uma lista?")
    tutor.answer("E como removo um item dela?")

    assert _sent(model.calls[1]) == [
        ("system", SYSTEM_PROMPT),
        ("human", "Como criar uma lista?"),
        ("ai", "resposta 1"),
        ("human", "E como removo um item dela?"),
    ]


def test_each_call_starts_with_exactly_what_the_previous_call_sent() -> None:
    # O cache de prompt da OpenAI só reaproveita o começo da entrada que for idêntico ao de uma chamada
    # recente. Se o histórico fosse reordenado, resumido ou cortado no começo, cada turno pagaria a
    # conversa inteira de novo pelo preço cheio.
    model = RecordingChatModel()
    tutor = Tutor(model)

    for question in ["pergunta 1", "pergunta 2", "pergunta 3"]:
        tutor.answer(question)

    for previous, current in zip(model.calls, model.calls[1:], strict=False):
        assert _sent(current)[: len(previous)] == _sent(previous)


def test_failed_answer_does_not_enter_the_history() -> None:
    # Uma pergunta sem resposta que ficasse no histórico iria em todas as chamadas seguintes, pagando
    # tokens à toa e sugerindo ao modelo que ela já foi respondida.
    model = RecordingChatModel(fail_on_call=2)
    tutor = Tutor(model)
    tutor.answer("pergunta respondida")

    with pytest.raises(RuntimeError):
        tutor.answer("pergunta que falhou")
    tutor.answer("pergunta seguinte")

    assert _sent(model.calls[2]) == [
        ("system", SYSTEM_PROMPT),
        ("human", "pergunta respondida"),
        ("ai", "resposta 1"),
        ("human", "pergunta seguinte"),
    ]


def test_docs_search_reaches_the_model_restricted_to_the_official_domains() -> None:
    # Sem o filtro, a busca vai à web aberta: qualquer página entra na resposta, inclusive uma com
    # instruções escondidas para o modelo.
    model = RecordingChatModel()
    tutor = Tutor(model, docs_search=True)

    tutor.answer("O que são t-strings?")

    assert model.tools == [{"type": "web_search", "filters": {"allowed_domains": list(DOCS_DOMAINS)}}]


def test_without_docs_search_the_tutor_has_no_tool_and_the_same_prompt() -> None:
    # É o braço de controle do experimento: só a busca pode mudar entre os dois braços.
    model = RecordingChatModel()
    tutor = Tutor(model)

    tutor.answer("O que são t-strings?")

    assert model.tools == []
    assert _sent(model.calls[0])[0] == ("system", SYSTEM_PROMPT)


def test_pages_cited_by_the_search_are_listed_after_the_answer() -> None:
    # A OpenAI exige que as fontes da busca fiquem visíveis para quem lê, e a CLI mostra só o texto: os
    # links ficariam nas anotações da resposta, fora da tela. Cada página aparece uma vez, na ordem.
    whatsnew = "https://docs.python.org/3/whatsnew/3.14.html"
    pep = "https://peps.python.org/pep-0750/"
    model = RecordingChatModel(
        reply_blocks=[
            {"type": "web_search_call", "id": "ws_1", "status": "completed"},
            {
                "type": "text",
                "text": "T-strings criam um Template.",
                "annotations": [
                    {"type": "url_citation", "url": whatsnew, "title": "What's new"},
                    {"type": "url_citation", "url": pep, "title": "PEP 750"},
                    {"type": "url_citation", "url": whatsnew, "title": "What's new"},
                ],
            },
        ]
    )
    tutor = Tutor(model, docs_search=True)

    answer = tutor.answer("O que são t-strings?")

    assert answer == f"T-strings criam um Template.\n\nFontes:\n- {whatsnew}\n- {pep}"


def _openai_error(error_class: type[openai.APIStatusError], status: int, code: str | None = None) -> Exception:
    request = httpx2.Request("POST", "https://api.openai.com/v1/responses")
    return error_class("erro simulado", response=httpx2.Response(status, request=request), body={"code": code})


@pytest.mark.parametrize(
    "error",
    [
        _openai_error(openai.AuthenticationError, 401),
        _openai_error(openai.PermissionDeniedError, 403),
        _openai_error(openai.RateLimitError, 429, "insufficient_quota"),
    ],
    ids=["chave-invalida", "sem-permissao", "sem-saldo"],
)
def test_rejected_key_or_account_is_not_reported_as_a_passing_failure(error: Exception) -> None:
    # Com a chave errada ou sem saldo, nenhuma pergunta vai ser respondida; "tente de novo" faria a
    # pessoa repetir perguntas que sempre falham, sem saber que o problema está na configuração.
    tutor = Tutor(RecordingChatModel(fail_on_call=1, failure=error))

    with pytest.raises(OpenAIAccountError):
        tutor.answer("Como criar uma lista?")


def test_rate_limit_is_a_passing_failure() -> None:
    # Limite de requisições por minuto passa sozinho: a conversa segue, e a próxima pergunta funciona.
    tutor = Tutor(
        RecordingChatModel(fail_on_call=1, failure=_openai_error(openai.RateLimitError, 429, "rate_limit_exceeded"))
    )

    with pytest.raises(AnswerUnavailableError):
        tutor.answer("Como criar uma lista?")
