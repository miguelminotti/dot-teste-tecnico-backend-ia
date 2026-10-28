"""Tutor de Python: monta a conversa com o LLM pelo LangChain e devolve a resposta."""

import openai
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

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
    """Responde perguntas de Python com um modelo de chat.

    Recebe o modelo pronto: a CLI passa o da OpenAI, e um teste pode passar um modelo falso do
    LangChain, sem rede nem custo.
    """

    def __init__(self, model: BaseChatModel) -> None:
        prompt = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("human", "{question}")])
        # LCEL: o prompt formata as mensagens, o modelo responde e o parser extrai o texto da resposta.
        self._chain = prompt | model | StrOutputParser()

    def answer(self, question: str) -> str:
        try:
            return self._chain.invoke({"question": question})
        except openai.APIError as error:
            # O cliente da OpenAI já tentou de novo nas falhas passageiras; aqui a falha é definitiva
            # para esta pergunta, e a conversa pode seguir.
            raise AnswerUnavailableError(f"o modelo não respondeu ({type(error).__name__})") from error
