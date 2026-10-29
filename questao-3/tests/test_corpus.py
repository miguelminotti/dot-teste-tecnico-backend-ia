from semantic_search.corpus import ArxivRecord, Section, extract_sections, is_candidate, parse_oai_records

# HTML no formato que o arXiv gera a partir do LaTeX (LaTeXML), reduzido ao que a extração usa.
PAPER_HTML = """
<html><body><article class="ltx_document">
<h1 class="ltx_title ltx_title_document">Título<span class="ltx_note ltx_role_thanks">Thanks: bolsa X</span></h1>
<div class="ltx_abstract"><p class="ltx_p">Resumo do HTML.</p></div>
<section class="ltx_section" id="S1">
  <h2 class="ltx_title ltx_title_section"><span class="ltx_tag ltx_tag_section">1 </span>Introduction</h2>
  <div class="ltx_para"><p class="ltx_p">We minimize the loss
    <math alttext="\\mathcal{L}" class="ltx_Math"><semantics><mi>L</mi><annotation>L</annotation></semantics></math>
    , as in prior work <cite class="ltx_cite">( Smith, 2025 )</cite> .<span class="ltx_note ltx_role_footnote">
    <sup class="ltx_note_mark">1</sup><span class="ltx_note_content">Nota de rodapé.</span></span></p></div>
  <figure class="ltx_figure"><figcaption class="ltx_caption">Figure 1: Arquitetura.</figcaption></figure>
  <section class="ltx_subsection" id="S1.SS1">
    <h3 class="ltx_title ltx_title_subsection"><span class="ltx_tag">1.1 </span>Setup</h3>
    <div class="ltx_para"><p class="ltx_p">Subsection text <cite class="ltx_cite">[ 3 , 4 ]</cite>.</p></div>
    <figure class="ltx_table"><table class="ltx_tabular"><tr><td>0.91</td></tr></table></figure>
    <figure class="ltx_figure"><div class="ltx_para"><p class="ltx_p">Prompt: You are a judge.</p></div></figure>
  </section>
</section>
<section class="ltx_bibliography" id="bib"><h2 class="ltx_title">References</h2>
  <ul><li class="ltx_bibitem">Smith. A paper. 2025.</li></ul></section>
<section class="ltx_appendix" id="A1"><h2 class="ltx_title">Appendix A Hyperparameters</h2>
  <section class="ltx_subsection" id="A1.SS1"><h3 class="ltx_title">A.1 Optimizer</h3>
  <div class="ltx_para"><p class="ltx_p">Learning rate 1e-5.</p></div></section></section>
</article></body></html>
"""


def test_body_keeps_sections_in_order_with_their_level_and_without_numbers() -> None:
    # A seção e o nível guiam a divisão em pedaços; o número ("1.1") não diz nada sobre o conteúdo.
    sections = extract_sections(PAPER_HTML)

    assert [(section.heading, section.level) for section in sections] == [("Introduction", 1), ("Setup", 2)]


def test_paragraph_belongs_only_to_its_own_section() -> None:
    # O parágrafo da subseção também está dentro da seção pai no HTML; contado nas duas, ele entraria
    # duplicado no corpus e pesaria em dobro na busca.
    sections = extract_sections(PAPER_HTML)

    assert sections[1] == Section(heading="Setup", level=2, paragraphs=("Subsection text.",))
    assert "Subsection text." not in " ".join(sections[0].paragraphs)


def test_list_items_stay_inside_their_paragraph_and_do_not_repeat() -> None:
    # O LaTeXML põe um ltx_para dentro de cada item de lista, e a lista dentro de outro ltx_para: contados
    # os dois, cada item entrava duas vezes (368 parágrafos repetidos no corpus).
    html = """
    <article class="ltx_document"><section class="ltx_section" id="S1">
      <h2 class="ltx_title ltx_title_section">Introduction</h2>
      <div class="ltx_para"><p class="ltx_p">Our contributions:</p><ul class="ltx_itemize">
        <li class="ltx_item"><div class="ltx_para"><p class="ltx_p">First item.</p></div></li>
        <li class="ltx_item"><div class="ltx_para"><p class="ltx_p">Second item.</p></div></li>
      </ul></div>
      <div class="ltx_para"><p class="ltx_p">Next paragraph.</p></div>
    </section></article>
    """

    assert extract_sections(html)[0].paragraphs == ("Our contributions: First item. Second item.", "Next paragraph.")


def test_references_appendix_footnotes_figures_and_tables_are_left_out() -> None:
    # Referências trariam os títulos de outros artigos para dentro deste, e a busca o devolveria por
    # assunto que ele só cita. Tabelas viram números soltos sem o cabeçalho. As subseções de apêndice e
    # os parágrafos dentro de figura (caixas de prompt) são casos reais do HTML do arXiv.
    sections = extract_sections(PAPER_HTML)
    text = " ".join(paragraph for section in sections for paragraph in section.paragraphs)

    for left_out in ["A paper", "Learning rate", "Nota de rodapé", "Arquitetura", "0.91", "You are a judge"]:
        assert left_out not in text
    assert "Optimizer" not in [section.heading for section in sections]


def test_numeric_citation_is_left_out_and_author_year_citation_stays() -> None:
    # "[3, 4]" não diz nada sem a lista de referências, que fica de fora; "(Smith, 2025)" é parte da frase.
    sections = extract_sections(PAPER_HTML)

    assert sections[1].paragraphs == ("Subsection text.",)
    assert "(Smith, 2025)" in sections[0].paragraphs[0]


def test_math_becomes_its_latex_source_and_spacing_is_normalized() -> None:
    # O MathML repete a fórmula (apresentação e anotação); o LaTeX do `alttext` aparece uma vez só.
    sections = extract_sections(PAPER_HTML)

    assert sections[0].paragraphs == ("We minimize the loss \\mathcal{L}, as in prior work (Smith, 2025).",)


OAI_PAGE = b"""<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"><ListRecords>
<record><header><identifier>oai:arXiv.org:2610.01938</identifier></header><metadata>
<arXiv xmlns="http://arxiv.org/OAI/arXiv/">
  <id>2610.01938</id>
  <authors><author><keyname>Silva</keyname><forenames>Ana B.</forenames></author>
    <author><keyname>Consortium</keyname></author></authors>
  <title>A rubric
    landscape</title>
  <categories>cs.CL cs.AI</categories>
  <license>http://creativecommons.org/licenses/by/4.0/</license>
  <abstract>  Resumo
    em duas linhas. </abstract>
</arXiv></metadata></record>
<resumptionToken cursor="0" completeListSize="2">token-2</resumptionToken>
</ListRecords></OAI-PMH>"""


def test_oai_page_gives_records_and_the_token_of_the_next_page() -> None:
    records, token = parse_oai_records(OAI_PAGE)

    assert records == [
        ArxivRecord(
            id="2610.01938",
            title="A rubric landscape",
            abstract="Resumo em duas linhas.",
            authors=("Ana B. Silva", "Consortium"),
            categories=("cs.CL", "cs.AI"),
            license="http://creativecommons.org/licenses/by/4.0/",
        )
    ]
    assert token == "token-2"


def _record(*, id: str = "2610.01938", categories: tuple[str, ...] = ("cs.CL",), license: str = "by") -> ArxivRecord:
    licenses = {
        "by": "http://creativecommons.org/licenses/by/4.0/",
        "zero": "http://creativecommons.org/publicdomain/zero/1.0/",
        "by-nc": "http://creativecommons.org/licenses/by-nc-sa/4.0/",
        "arxiv": "http://arxiv.org/licenses/nonexclusive-distrib/1.0/",
    }
    return ArxivRecord(id=id, title="t", abstract="a", authors=("x",), categories=categories, license=licenses[license])


def test_candidate_is_a_paper_of_the_month_with_the_category_as_primary_and_an_open_license() -> None:
    # O id diz o mês da primeira submissão; a data "created" do OAI não serve (um artigo de 2023
    # aparece com created em outubro de 2026). Só licença que permite redistribuir o texto entra.
    assert is_candidate(_record(), month="2610", category="cs.CL")
    assert is_candidate(_record(license="zero"), month="2610", category="cs.CL")
    assert not is_candidate(_record(id="2303.15619"), month="2610", category="cs.CL")
    assert not is_candidate(_record(categories=("cs.LG", "cs.CL")), month="2610", category="cs.CL")
    assert not is_candidate(_record(license="by-nc"), month="2610", category="cs.CL")
    assert not is_candidate(_record(license="arxiv"), month="2610", category="cs.CL")
