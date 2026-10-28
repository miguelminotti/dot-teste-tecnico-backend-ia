from typing import Any

import pytest
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from chatbot.tutor import SYSTEM_PROMPT, Tutor


class RecordingChatModel(BaseChatModel):
    """Modelo falso: guarda as mensagens de cada chamada e responde "resposta N" na chamada N.

    Os modelos falsos do `langchain-core` (`FakeListChatModel`, `GenericFakeChatModel` e afins)
    respondem, mas descartam as mensagens que recebem, e o que estes testes conferem é justamente o
    que o `Tutor` envia. Nenhum deles falha numa chamada escolhida fora do streaming, e o `Tutor` usa
    `invoke`.
    """

    calls: list[list[BaseMessage]] = Field(default_factory=list)
    # Número da chamada (a partir de 1) que falha, para simular a API fora do ar.
    fail_on_call: int | None = None

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
            raise RuntimeError("falha simulada")
        return ChatResult(generations=[ChatGeneration(message=AIMessage(f"resposta {len(self.calls)}"))])


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
