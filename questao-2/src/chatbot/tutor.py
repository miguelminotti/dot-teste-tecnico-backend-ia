"""Tutor de Python: monta a conversa com o LLM pelo LangChain e devolve a resposta."""

import openai
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Prompt de partida, mínimo de propósito: cada regra nova (corrigir premissa falsa, citar a versão do
# Python, admitir incerteza) entra quando uma avaliação mostrar a falha que ela corrige. O bloco
# ```python é contrato com a avaliação, que extrai e executa os snippets por ele.
# Chaves "{" e "}" aqui seriam lidas como variáveis do template; o texto não deve ter nenhuma.
SYSTEM_PROMPT = """\
Você é um professor de programação em Python e responde dúvidas sobre a linguagem.

- Responda no idioma da pergunta.
- Dê uma explicação detalhada e didática, com exemplos de código.
- Escreva o código em blocos ```python.
- Se a pergunta não for sobre programação em Python, diga com educação que só responde sobre Python e \
convide a pessoa a perguntar algo sobre a linguagem."""


class AnswerUnavailableError(Exception):
    """O modelo não respondeu: falha de rede, limite de uso da API ou chave inválida."""


class Tutor:
    """Uma conversa com o tutor: responde perguntas de Python lembrando os turnos anteriores.

    Cada instância é uma conversa; uma conversa nova é um `Tutor` novo. Recebe o modelo pronto: a
    CLI passa o da OpenAI, e um teste pode passar um modelo falso do LangChain, sem rede nem custo.
    """

    def __init__(self, model: BaseChatModel) -> None:
        # Ordem fixa: sistema, turnos anteriores, pergunta nova. Assim cada chamada começa com
        # exatamente o que a anterior enviou, e o cache de prompt da OpenAI reaproveita esse começo.
        prompt = ChatPromptTemplate.from_messages(
            [("system", SYSTEM_PROMPT), MessagesPlaceholder("history"), ("human", "{question}")]
        )
        # LCEL: o prompt formata as mensagens, o modelo responde e o parser extrai o texto da resposta.
        self._chain = prompt | model | StrOutputParser()
        # Histórico numa lista explícita, e não nas classes de histórico do LangChain, deprecadas em
        # favor da persistência do LangGraph (ADR 0001). Só cresce no fim: resumir, cortar ou
        # reescrever um turno antigo mudaria o começo da entrada e zeraria o cache dali em diante.
        self._history: list[BaseMessage] = []

    def answer(self, question: str) -> str:
        try:
            reply = self._chain.invoke({"history": self._history, "question": question})
        except openai.APIError as error:
            # O cliente da OpenAI já tentou de novo nas falhas passageiras; aqui a falha é definitiva
            # para esta pergunta, e a conversa pode seguir.
            raise AnswerUnavailableError(f"o modelo não respondeu ({type(error).__name__})") from error
        # O turno só entra no histórico depois da resposta: uma pergunta que falhou não vai junto nas
        # próximas chamadas, como se tivesse sido respondida.
        self._history += [HumanMessage(question), AIMessage(reply)]
        return reply
