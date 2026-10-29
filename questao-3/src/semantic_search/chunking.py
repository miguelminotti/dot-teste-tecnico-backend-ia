"""Divisão dos artigos em pedaços (chunks), a unidade que vira embedding e que a busca devolve."""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from semantic_search.corpus import Document

# Teto em palavras, e não em tokens de um modelo: o mesmo corte serve a todos os modelos comparados, e a
# diferença entre eles mede só o modelo. No corpus, uma palavra dá cerca de 1,8 token (fórmulas e nomes
# quebram em muitos tokens), então 200 palavras ficam em torno de 360 tokens, abaixo dos 512 do e5.
DEFAULT_MAX_WORDS = 200

# Fim de frase: pontuação final, espaço e começo de frase (maiúscula, número, aspas ou parêntese).
_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[\"“(\[]?[A-Z0-9])")
# Abreviações comuns em artigos, depois das quais um ponto não fecha a frase.
_ABBREVIATIONS = ("e.g.", "i.e.", "et al.", "etc.", "vs.", "cf.", "Fig.", "Figs.", "Eq.", "Eqs.", "Sec.", "No.")


@dataclass(frozen=True, slots=True, kw_only=True)
class Chunk:
    """Um pedaço de artigo: o texto e de onde ele veio."""

    id: str
    paper_id: str
    section: str
    # Posição do parágrafo no corpo do artigo, a mesma das evidências das consultas; None no resumo.
    paragraph: int | None
    text: str


def chunk_documents(documents: Sequence[Document], *, max_words: int = DEFAULT_MAX_WORDS) -> list[Chunk]:
    """O título com o resumo, e cada parágrafo do corpo, viram um pedaço cada.

    O parágrafo é a unidade natural do texto; o que passa de `max_words` (o parágrafo, ou o título com o
    resumo) é dividido entre frases, para que o fim não seja cortado pelo limite de tokens do modelo.
    """
    chunks = []
    for document in documents:
        # Título terminado em "?" ou "!" não ganha outro ponto ("Do models agree?. We...").
        title = document.title if document.title.endswith((".", "?", "!")) else f"{document.title}."
        pieces: list[tuple[str, int | None, str]] = [
            ("Abstract", None, piece) for piece in _pack(f"{title} {document.abstract}", max_words)
        ]
        paragraphs = [(section.heading, text) for section in document.sections for text in section.paragraphs]
        for index, (heading, text) in enumerate(paragraphs):
            pieces += [(heading, index, piece) for piece in _pack(text, max_words)]
        chunks += [
            Chunk(id=f"{document.id}#{number}", paper_id=document.id, section=section, paragraph=paragraph, text=text)
            for number, (section, paragraph, text) in enumerate(pieces)
        ]
    return chunks


def _pack(text: str, max_words: int) -> list[str]:
    """Junta frases seguidas em pedaços de até `max_words`; uma frase maior que o teto fica sozinha."""
    if len(text.split()) <= max_words:
        return [text]
    pieces: list[str] = []
    current: list[str] = []
    for sentence in split_sentences(text):
        if current and len(" ".join([*current, sentence]).split()) > max_words:
            pieces.append(" ".join(current))
            current = []
        current.append(sentence)
    pieces.append(" ".join(current))
    return pieces


def split_sentences(text: str) -> list[str]:
    """Frases do texto, sem quebrar em abreviações ("et al.", "e.g.") nem em números ("0.87")."""
    sentences = []
    start = 0
    for boundary in _BOUNDARY.finditer(text):
        before = text[start : boundary.start()]
        if before.endswith(_ABBREVIATIONS):
            continue
        sentences.append(before)
        start = boundary.end()
    sentences.append(text[start:])
    return [sentence for sentence in sentences if sentence]
