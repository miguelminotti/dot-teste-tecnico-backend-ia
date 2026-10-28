from semantic_search.corpus import Document, Section
from semantic_search.evaluation.queries import Passage, choose_passages, label_relevance, quote_in_passage

LONG = " ".join(["palavra"] * 80)


def _document(paper_id: str, *paragraphs: str) -> Document:
    return Document(
        id=paper_id,
        title=f"Título {paper_id}",
        abstract="Resumo.",
        sections=(Section(heading="Method", level=1, paragraphs=paragraphs),),
    )


def test_passages_come_one_per_paper_from_long_paragraphs_and_repeat_with_the_seed() -> None:
    # Parágrafo curto ("Results are in Table 2.") não sustenta uma pergunta de detalhe; a mesma semente
    # tem de dar os mesmos trechos, para que o conjunto possa ser refeito.
    documents = [_document(f"2610.0000{index}", "Curto demais.", f"{LONG} {index}") for index in range(5)]

    passages = choose_passages(documents, count=3, seed=7)

    assert len({passage.paper_id for passage in passages}) == 3
    assert all(passage.paragraph_index == 1 and passage.section == "Method" for passage in passages)
    assert passages == choose_passages(documents, count=3, seed=7)


def test_paper_without_a_long_paragraph_is_skipped() -> None:
    documents = [_document("2610.00001", "Curto."), _document("2610.00002", LONG)]

    assert [passage.paper_id for passage in choose_passages(documents, count=2, seed=1)] == ["2610.00002"]


def test_evidence_quote_must_be_copied_from_the_passage() -> None:
    # A citação é o que marca o pedaço relevante na avaliação; uma citação reescrita pelo modelo não
    # casa com nenhum pedaço, e a consulta pareceria sem resposta no corpus.
    passage = Passage(
        paper_id="p", section="s", paragraph_index=0, text="The audit agreed on 195/200 outputs  (97.5%)."
    )

    assert quote_in_passage("agreed on 195/200 outputs (97.5%)", passage)
    assert not quote_in_passage("agreed on 195 of 200 outputs (97.5%)", passage)
    assert not quote_in_passage("", passage)


def test_source_paper_is_relevant_and_a_judge_that_disagrees_flags_the_query() -> None:
    # A consulta foi escrita a partir do artigo de origem; se o juiz não o acha relevante, a consulta
    # ficou vaga ou o juiz errou, e alguém precisa olhar antes de ela valer.
    relevant, needs_review = label_relevance(judged={"2610.2", "2610.3"}, source="2610.1")
    assert relevant == ["2610.1", "2610.2", "2610.3"]
    assert needs_review

    relevant, needs_review = label_relevance(judged={"2610.1"}, source="2610.1")
    assert relevant == ["2610.1"]
    assert not needs_review


def test_topic_query_without_relevant_papers_is_flagged() -> None:
    # Um tema que o juiz não liga a nenhum artigo não mede nada.
    assert label_relevance(judged=set(), source=None) == ([], True)
    assert label_relevance(judged={"2610.1"}, source=None) == (["2610.1"], False)
