from semantic_search.chunking import Chunk, chunk_documents, split_sentences
from semantic_search.corpus import Document, Section


def _document(*paragraphs: str) -> Document:
    return Document(
        id="2610.00001",
        title="Um título",
        abstract="Um resumo curto.",
        sections=(
            Section(heading="Introduction", level=1, paragraphs=paragraphs[:1]),
            Section(heading="Method", level=1, paragraphs=paragraphs[1:]),
        ),
    )


def test_title_and_abstract_are_the_first_chunk_and_each_paragraph_is_one_chunk() -> None:
    # O resumo é o que resume o artigo inteiro; os parágrafos guardam a seção e a posição, que ligam o
    # pedaço à frase de evidência das consultas de detalhe.
    chunks = chunk_documents([_document("Primeiro parágrafo.", "Segundo parágrafo.")], max_words=200)

    assert chunks == [
        Chunk(
            id="2610.00001#0",
            paper_id="2610.00001",
            section="Abstract",
            paragraph=None,
            text="Um título. Um resumo curto.",
        ),
        Chunk(
            id="2610.00001#1", paper_id="2610.00001", section="Introduction", paragraph=0, text="Primeiro parágrafo."
        ),
        Chunk(id="2610.00001#2", paper_id="2610.00001", section="Method", paragraph=1, text="Segundo parágrafo."),
    ]


def test_long_paragraph_is_split_between_sentences_without_losing_text() -> None:
    # Acima do limite do modelo, o fim do parágrafo seria cortado em silêncio e nunca seria encontrado.
    sentences = [f"Frase número {index} com algumas palavras a mais." for index in range(12)]
    paragraph = " ".join(sentences)

    chunks = chunk_documents([_document(paragraph)], max_words=20)[1:]

    assert len(chunks) > 1
    assert all(len(chunk.text.split()) <= 20 for chunk in chunks)
    assert " ".join(chunk.text for chunk in chunks) == paragraph
    assert {chunk.paragraph for chunk in chunks} == {0}


def test_sentence_split_does_not_break_abbreviations_or_numbers() -> None:
    # "et al." e "e.g." aparecem em quase todo artigo; quebrar ali separaria uma citação da frase dela.
    text = "As shown by Chen et al. (2025), accuracy rose to 0.87 on average. Other tasks, e.g. QA, did not. Done."

    assert split_sentences(text) == [
        "As shown by Chen et al. (2025), accuracy rose to 0.87 on average.",
        "Other tasks, e.g. QA, did not.",
        "Done.",
    ]
