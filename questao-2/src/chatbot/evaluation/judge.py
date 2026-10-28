"""LLM como juiz: correção técnica e qualidade didática de cada resposta do tutor."""

from collections.abc import Sequence

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

# Os critérios estão definidos em docs/avaliacao.md; este texto é a versão deles que o juiz lê.
JUDGE_PROMPT = """\
Você avalia as respostas de um tutor de Python para quem está aprendendo. Você recebe a conversa até \
aqui, a pergunta atual, os pontos-chave numerados que a resposta precisa cobrir e a resposta do tutor.

Em cada item, escreva a justificativa antes do veredito.

key_points: um item por ponto-chave, na ordem da lista. O ponto está coberto se a resposta transmite a \
ideia dele, mesmo com outras palavras. Um exemplo dentro do ponto-chave (como `list(range(5))`) ilustra \
o ponto: outro exemplo que mostre a mesma coisa também cobre.

Critérios, cada um julgado separadamente; na dúvida, o critério falha:

- factual_accuracy: a resposta não afirma nada tecnicamente errado nem enganoso, inclusive no código. \
Deixar de mencionar algo não é erro aqui; a cobertura é medida pelos pontos-chave.
- answers_question: responde logo o que foi perguntado, sem desviar do assunto.
- step_by_step: quando a resposta ensina um procedimento, ele vem em etapas, na ordem em que se faz. \
Se a pergunta não pede um procedimento, o critério passa.
- examples: tem exemplo de código ou analogia que ajuda a entender, e não decorativo. Se a pergunta \
não pede exemplo (uma recusa por estar fora do escopo, por exemplo), o critério passa.
- level_of_detail: detalhada o bastante para quem está aprendendo entender, sem encher com \
informação que não ajuda a responder.
- language: responde no idioma da pergunta."""


class KeyPointCheck(BaseModel):
    # A ordem dos campos é a ordem em que o modelo os escreve: a justificativa vem antes do veredito,
    # para que o veredito saia do raciocínio, e não o raciocínio seja inventado para justificá-lo.
    reasoning: str = Field(description="Onde a resposta cobre o ponto, ou o que falta.")
    covered: bool


class Criterion(BaseModel):
    reasoning: str = Field(description="Justificativa do veredito, citando a resposta.")
    passed: bool


class TurnVerdict(BaseModel):
    key_points: list[KeyPointCheck] = Field(description="Um item por ponto-chave, na mesma ordem da lista.")
    factual_accuracy: Criterion
    answers_question: Criterion
    step_by_step: Criterion
    examples: Criterion
    level_of_detail: Criterion
    language: Criterion


# Critérios de passa ou falha; a cobertura dos pontos-chave é contada à parte.
CRITERIA: tuple[str, ...] = tuple(name for name in TurnVerdict.model_fields if name != "key_points")


def judge_turn(
    judge: BaseChatModel,
    *,
    previous_turns: Sequence[tuple[str, str]],
    question: str,
    key_points: Sequence[str],
    answer: str,
) -> TurnVerdict:
    """Julga uma resposta; `previous_turns` são os pares (pergunta, resposta) anteriores da conversa."""
    conversation = "\n\n".join(f"**Aluno:** {asked}\n\n**Tutor:** {answered}" for asked, answered in previous_turns)
    points = "\n".join(f"{number}. {point}" for number, point in enumerate(key_points, 1))
    # Mensagens montadas direto, sem template: a resposta tem chaves de dicionário e f-string, que um
    # template do LangChain tentaria ler como variáveis.
    content = (
        f"## Conversa até aqui\n\n{conversation or '(primeira pergunta da conversa)'}\n\n"
        f"## Pergunta atual\n\n{question}\n\n"
        f"## Pontos-chave\n\n{points}\n\n"
        f"## Resposta do tutor\n\n{answer}"
    )
    verdict = judge.with_structured_output(TurnVerdict).invoke([SystemMessage(JUDGE_PROMPT), HumanMessage(content)])
    if not isinstance(verdict, TurnVerdict):
        raise TypeError(f"o juiz devolveu {type(verdict).__name__}, e não um TurnVerdict")
    # Com um item a mais ou a menos, não dá para saber qual ponto o juiz pulou: melhor falhar o turno
    # que contar a cobertura errada.
    if len(verdict.key_points) != len(key_points):
        raise ValueError(f"o juiz julgou {len(verdict.key_points)} pontos-chave, e eram {len(key_points)}")
    return verdict
