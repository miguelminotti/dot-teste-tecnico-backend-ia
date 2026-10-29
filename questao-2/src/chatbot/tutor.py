"""Tutor de Python: monta a conversa com o LLM pelo LangChain e devolve a resposta."""

import openai
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from chatbot.docs_search import WEB_SEARCH_TOOL
from chatbot.settings import Settings

# Prompt mínimo de propósito: cada regra entra quando uma avaliação mostra a falha que ela corrige
# (docs/avaliacao.md). O bloco ```python é contrato com a avaliação, que extrai e executa os snippets
# por ele.
# - "O essencial na própria resposta": o gpt-5.4-mini deixava propriedades e operações básicas como
#   oferta ("Se quiser, posso mostrar...") e cobria metade dos pontos do exemplo do enunciado.
# - "A saída em ```text": o gpt-5.4-mini punha a saída do programa em ```python, que não é código.
# Chaves "{" e "}" aqui seriam lidas como variáveis do template; o texto não deve ter nenhuma.
SYSTEM_PROMPT = """\
Você é um professor de programação em Python e responde dúvidas sobre a linguagem.

- Responda no idioma da pergunta.
- Dê uma explicação detalhada e didática, com exemplos de código.
- Explique o essencial na própria resposta: o que o recurso é, as propriedades principais e as \
operações mais usadas. Não deixe o essencial como oferta para depois.
- Escreva o código em blocos ```python e a saída do programa em blocos ```text.
- Se a pergunta não for sobre programação em Python, diga com educação que só responde sobre Python e \
convide a pessoa a perguntar algo sobre a linguagem."""

# Regra acrescentada só com a busca ligada. Sem ela, o modelo buscaria em toda pergunta, e a pergunta
# sobre listas pagaria uma busca (US$ 0,01 mais as páginas lidas) para responder o que ele já sabe.
# "Se uma sintaxe existe ou é permitida": sem esse caso, o modelo só buscava quando a pergunta citava
# uma versão, e respondia com certeza, e errado, que `except A, B:` é inválido (o 3.14 passou a aceitar).
DOCS_SEARCH_RULE = """
- Consulte a documentação oficial com a busca antes de responder sobre uma versão específica do \
Python, um recurso recente, uma biblioteca, ou se uma sintaxe, função ou módulo existe ou é permitido: \
a linguagem muda a cada versão, e o que era inválido pode ter passado a valer. No básico da linguagem, \
responda sem buscar."""


class AnswerUnavailableError(Exception):
    """O modelo não respondeu a esta pergunta, por uma falha passageira: rede, servidor ou limite por minuto."""


class OpenAIAccountError(Exception):
    """A OpenAI recusou a chave ou a conta (chave inválida, sem permissão, sem saldo): nenhuma pergunta vai
    ser respondida até a configuração mudar."""


class Tutor:
    """Uma conversa com o tutor: responde perguntas de Python lembrando os turnos anteriores.

    Cada instância é uma conversa; uma conversa nova é um `Tutor` novo. Recebe o modelo pronto: a
    CLI passa o da OpenAI, e um teste pode passar um modelo falso do LangChain, sem rede nem custo.
    """

    def __init__(self, model: BaseChatModel, *, docs_search: bool = False) -> None:
        system = SYSTEM_PROMPT + DOCS_SEARCH_RULE if docs_search else SYSTEM_PROMPT
        # Ordem fixa: sistema, turnos anteriores, pergunta nova. Assim cada chamada começa com
        # exatamente o que a anterior enviou, e o cache de prompt da OpenAI reaproveita esse começo.
        prompt = ChatPromptTemplate.from_messages(
            [("system", system), MessagesPlaceholder("history"), ("human", "{question}")]
        )
        responder = model.bind_tools([WEB_SEARCH_TOOL]) if docs_search else model
        # LCEL: o prompt formata as mensagens, o modelo responde e o último passo extrai o texto.
        self._chain = prompt | responder | _text_with_sources
        # Histórico numa lista explícita, e não nas classes de histórico do LangChain, deprecadas em
        # favor da persistência do LangGraph (ADR 0001). Só cresce no fim: resumir, cortar ou
        # reescrever um turno antigo mudaria o começo da entrada e zeraria o cache dali em diante.
        self._history: list[BaseMessage] = []

    def answer(self, question: str) -> str:
        try:
            reply = self._chain.invoke({"history": self._history, "question": question})
        except openai.APIError as error:
            if _account_rejected(error):
                raise OpenAIAccountError(
                    f"a OpenAI recusou a chave ou a conta ({type(error).__name__}): confira a OPENAI_API_KEY e o "
                    "saldo da conta"
                ) from error
            # O cliente da OpenAI já tentou de novo nas falhas passageiras; aqui a falha é definitiva
            # para esta pergunta, e a conversa pode seguir.
            raise AnswerUnavailableError(f"o modelo não respondeu ({type(error).__name__})") from error
        # O turno só entra no histórico depois da resposta: uma pergunta que falhou não vai junto nas
        # próximas chamadas, como se tivesse sido respondida.
        self._history += [HumanMessage(question), AIMessage(reply)]
        return reply


def _account_rejected(error: openai.APIError) -> bool:
    """Chave inválida (401), sem permissão (403) ou sem saldo (429 com `insufficient_quota`). O 429 comum,
    de limite por minuto, passa sozinho e não entra aqui."""
    if isinstance(error, openai.AuthenticationError | openai.PermissionDeniedError):
        return True
    return isinstance(error, openai.RateLimitError) and error.code == "insufficient_quota"


def create_tutor(settings: Settings) -> Tutor:
    """O tutor com o modelo da OpenAI configurado; a CLI e a avaliação usam este mesmo."""
    # Responses API com e sem busca: a ferramenta de busca só existe nela, e os dois braços do
    # experimento precisam da mesma API para que a comparação meça só a busca.
    model = ChatOpenAI(model=settings.model, use_responses_api=True)
    return Tutor(model, docs_search=settings.docs_search)


def _text_with_sources(message: AIMessage) -> str:
    """Texto da resposta, com as páginas citadas pela busca listadas no fim.

    A OpenAI exige que as fontes da busca fiquem visíveis para quem lê. Elas vêm como anotações nos
    blocos de texto, que a CLI não mostra; aqui viram uma lista, uma linha por página.
    """
    blocks = message.content if isinstance(message.content, list) else []
    sources = [
        annotation["url"]
        for block in blocks
        if isinstance(block, dict)
        for annotation in block.get("annotations") or []
        if annotation.get("type") == "url_citation"
    ]
    if not sources:
        return message.text
    listed = "\n".join(f"- {url}" for url in dict.fromkeys(sources))
    return f"{message.text}\n\nFontes:\n{listed}"
