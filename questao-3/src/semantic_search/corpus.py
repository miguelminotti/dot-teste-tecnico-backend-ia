"""Montagem do corpus: artigos recentes do arXiv, com licença aberta, em texto limpo e com as seções.

Uso, na pasta da questão: uv run semantic-search-corpus

1. Colhe os metadados de um intervalo de datas pelo OAI-PMH do arXiv (título, resumo, autores,
   categorias e licença de cada artigo).
2. Fica com os candidatos: artigos do mês pedido, com a categoria pedida como principal e licença que
   permite redistribuir o texto.
3. Sorteia os candidatos com semente fixa e baixa o HTML de cada um até juntar o tamanho pedido.
4. Extrai do HTML as seções do corpo, sem referências, apêndices, notas, figuras e tabelas, e grava um
   artigo por linha em JSONL.
"""

import argparse
import json
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from pathlib import Path

from bs4 import BeautifulSoup, Tag

OAI_URL = "https://oaipmh.arxiv.org/oai"
HTML_URL = "https://arxiv.org/html/{id}"
# O arXiv pede um intervalo entre requisições automáticas; 3 s é o que a documentação da API sugere.
REQUEST_INTERVAL_SECONDS = 3.0
_USER_AGENT = "dot-teste-tecnico/0.1 (questao-3, corpus de busca semantica)"
_NS = {"oai": "http://www.openarchives.org/OAI/2.0/", "arxiv": "http://arxiv.org/OAI/arXiv/"}

# Licenças que permitem redistribuir o texto no repositório, com atribuição. As não comerciais e a
# licença padrão do arXiv (só distribuição pelo próprio arXiv) ficam de fora.
OPEN_LICENSES = frozenset(
    {
        "http://creativecommons.org/licenses/by/4.0/",
        "http://creativecommons.org/publicdomain/zero/1.0/",
    }
)

# Nível de cada tipo de seção do LaTeXML; a ordem guia a divisão em pedaços nas próximas etapas.
_SECTION_LEVELS = {"ltx_section": 1, "ltx_subsection": 2, "ltx_subsubsection": 3, "ltx_paragraph": 4}
# O que sai do HTML antes da extração: apêndices são sobretudo detalhes de experimento (e as subseções
# deles seriam lidas como seções do corpo), figuras e tabelas viram números soltos ou caixas de prompt
# sem contexto, e `ltx_tag` é a numeração (de seção, equação e item de lista), que não diz nada sobre o
# conteúdo. As referências não precisam sair: a bibliografia não tem parágrafos (`ltx_para`).
_LEFT_OUT = ["section.ltx_appendix", ".ltx_note", "figure", "nav", ".ltx_tag"]
_NUMERIC_CITATION = re.compile(r"\[[\d,;–-]+\]")
# Menos palavras que isso no corpo é conversão do LaTeX que falhou, não artigo.
MIN_BODY_WORDS = 1500


@dataclass(frozen=True, slots=True, kw_only=True)
class ArxivRecord:
    """Metadados de um artigo, como o OAI-PMH do arXiv entrega."""

    id: str
    title: str
    abstract: str
    authors: tuple[str, ...]
    # A primeira é a categoria principal; as outras são listagens cruzadas.
    categories: tuple[str, ...]
    license: str


@dataclass(frozen=True, slots=True, kw_only=True)
class Section:
    """Uma seção do corpo do artigo: o título sem número, o nível (1 = seção) e os parágrafos."""

    heading: str
    level: int
    paragraphs: tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class Document:
    """Um artigo do corpus, como as etapas de busca e avaliação o leem."""

    id: str
    title: str
    abstract: str
    sections: tuple[Section, ...]
    url: str = ""


def load_documents(path: Path) -> list[Document]:
    """Artigos do corpus em JSONL, na ordem do arquivo."""
    documents = []
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = json.loads(line)
        sections = tuple(
            Section(heading=section["heading"], level=section["level"], paragraphs=tuple(section["paragraphs"]))
            for section in raw["sections"]
        )
        documents.append(
            Document(id=raw["id"], title=raw["title"], abstract=raw["abstract"], sections=sections, url=raw["url"])
        )
    return documents


def parse_oai_records(page: bytes) -> tuple[list[ArxivRecord], str | None]:
    """Registros de uma página do OAI-PMH e o token da página seguinte (None na última)."""
    root = ET.fromstring(page)
    records = []
    for metadata in root.iterfind(".//arxiv:arXiv", _NS):
        authors = tuple(
            " ".join(filter(None, [_text(author, "forenames"), _text(author, "keyname")]))
            for author in metadata.iterfind("arxiv:authors/arxiv:author", _NS)
        )
        records.append(
            ArxivRecord(
                id=_text(metadata, "id"),
                title=_text(metadata, "title"),
                abstract=_text(metadata, "abstract"),
                authors=authors,
                categories=tuple(_text(metadata, "categories").split()),
                license=_text(metadata, "license"),
            )
        )
    token = root.find(".//oai:resumptionToken", _NS)
    return records, (token.text or "").strip() or None if token is not None else None


def _text(element: ET.Element, tag: str) -> str:
    """Texto de um campo do arXiv com o espaço normalizado (títulos e resumos vêm quebrados em linhas)."""
    return " ".join((element.findtext(f"arxiv:{tag}", default="", namespaces=_NS)).split())


def is_candidate(record: ArxivRecord, *, month: str, category: str) -> bool:
    """O artigo é do mês pedido (AAMM), tem a categoria pedida como principal e licença aberta.

    O mês vem do id, atribuído na primeira submissão. A data `created` do OAI não serve: um artigo de
    2023 aparece com `created` em outubro de 2026.
    """
    return (
        record.id.startswith(f"{month}.") and record.categories[:1] == (category,) and record.license in OPEN_LICENSES
    )


def extract_sections(html: str) -> list[Section]:
    """Seções do corpo do artigo, na ordem, a partir do HTML que o arXiv gera do LaTeX (LaTeXML)."""
    soup = BeautifulSoup(html, "html.parser")
    for element in soup.select(", ".join(_LEFT_OUT)):
        element.decompose()
    for math in soup.find_all("math"):
        # O MathML traz a fórmula duas vezes (apresentação e anotação); o LaTeX do `alttext`, uma.
        math.replace_with(f" {math.get('alttext', '')} ")
    for cite in soup.find_all("cite"):
        # "[3, 4]" não diz nada sem a lista de referências; "(Smith, 2025)" faz parte da frase e fica.
        if _NUMERIC_CITATION.fullmatch(cite.get_text("").replace(" ", "")):
            cite.decompose()

    sections = []
    for section in soup.find_all("section"):
        classes = section.get_attribute_list("class")
        level = next((_SECTION_LEVELS[name] for name in classes if name in _SECTION_LEVELS), None)
        if level is None:
            continue
        heading = section.find(["h2", "h3", "h4", "h5", "h6"], recursive=False)
        # Só os parágrafos desta seção: os da subseção também estão dentro dela no HTML.
        paragraphs = [
            _clean(paragraph.get_text(" "))
            for paragraph in section.find_all(class_="ltx_para")
            if paragraph.find_parent("section") is section
        ]
        sections.append(
            Section(
                heading=_clean(heading.get_text(" ")) if isinstance(heading, Tag) else "",
                level=level,
                paragraphs=tuple(paragraph for paragraph in paragraphs if paragraph),
            )
        )
    return sections


def _clean(text: str) -> str:
    """Espaço normalizado, sem o espaço que os elementos do HTML deixam antes da pontuação e dentro de parênteses."""
    text = " ".join(text.split())
    text = re.sub(r"\s+([.,;:!?)\]])", r"\1", text)
    return re.sub(r"([(\[])\s+", r"\1", text)


def harvest(*, from_date: str, until_date: str, oai_set: str = "cs") -> Iterator[ArxivRecord]:
    """Todos os registros do conjunto alterados no intervalo de datas, página a página."""
    params = {"verb": "ListRecords", "metadataPrefix": "arXiv", "set": oai_set, "from": from_date, "until": until_date}
    while True:
        records, token = parse_oai_records(_get(f"{OAI_URL}?{urllib.parse.urlencode(params)}"))
        yield from records
        if token is None:
            return
        params = {"verb": "ListRecords", "resumptionToken": token}


def _get(url: str) -> bytes:
    """Baixa a URL respeitando o intervalo entre requisições e o `Retry-After` do arXiv quando ocupado."""
    for attempt in range(5):
        time.sleep(REQUEST_INTERVAL_SECONDS)
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, headers={"User-Agent": _USER_AGENT}), timeout=120
            ) as response:
                body: bytes = response.read()
                return body
        except urllib.error.HTTPError as error:
            if error.code != 503 or attempt == 4:
                raise
            time.sleep(int(error.headers.get("Retry-After", "30")))
    raise AssertionError("inalcançável")


def _cached_html(record_id: str, cache: Path) -> str:
    """HTML do artigo, baixado uma vez só: mudar a extração não pede baixar os artigos de novo."""
    path = cache / f"{record_id}.html"
    if not path.exists():
        cache.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_get(HTML_URL.format(id=record_id)))
    return path.read_text(encoding="utf-8")


def build_document(record: ArxivRecord, sections: list[Section]) -> dict[str, object]:
    """Uma linha do corpus: metadados com a atribuição (autores, licença, link) e as seções do corpo."""
    return {
        "id": record.id,
        "url": f"https://arxiv.org/abs/{record.id}",
        "title": record.title,
        "authors": list(record.authors),
        "categories": list(record.categories),
        "license": record.license,
        "abstract": record.abstract,
        "sections": [asdict(section) for section in sections],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Monta o corpus com artigos recentes do arXiv.")
    parser.add_argument("--from-date", default="2026-10-01", help="início da colheita no OAI-PMH (AAAA-MM-DD)")
    parser.add_argument("--until-date", default="2026-10-27", help="fim da colheita no OAI-PMH (AAAA-MM-DD)")
    parser.add_argument("--month", default="2610", help="mês da primeira submissão, como no id (AAMM)")
    parser.add_argument("--category", default="cs.CL", help="categoria principal do arXiv")
    parser.add_argument("--size", type=int, default=100, help="número de artigos do corpus")
    parser.add_argument("--seed", type=int, default=42, help="semente do sorteio dos candidatos")
    parser.add_argument("--out", type=Path, default=Path("data/corpus.jsonl"))
    parser.add_argument(
        "--html-cache", type=Path, default=Path("data/html"), help="pasta do HTML baixado (fora do git)"
    )
    args = parser.parse_args()

    candidates = sorted(
        (
            record
            for record in harvest(from_date=args.from_date, until_date=args.until_date)
            if is_candidate(record, month=args.month, category=args.category)
        ),
        key=lambda record: record.id,
    )
    # Um registro aparece mais de uma vez quando o artigo muda no intervalo; fica a última versão.
    candidates = list({record.id: record for record in candidates}.values())
    print(f"{len(candidates)} candidatos", file=sys.stderr)
    random.Random(args.seed).shuffle(candidates)

    documents: list[dict[str, object]] = []
    for record in candidates:
        if len(documents) == args.size:
            break
        try:
            html = _cached_html(record.id, args.html_cache)
        except urllib.error.HTTPError as error:
            # Nem todo artigo tem HTML: a conversão do LaTeX falha em parte deles.
            print(f"{record.id}: sem HTML ({error.code})", file=sys.stderr)
            continue
        sections = extract_sections(html)
        words = sum(len(paragraph.split()) for section in sections for paragraph in section.paragraphs)
        if words < MIN_BODY_WORDS:
            print(f"{record.id}: corpo com {words} palavras, conversão incompleta", file=sys.stderr)
            continue
        documents.append(build_document(record, sections))
        print(f"{len(documents)}/{args.size} {record.id} ({words} palavras)", file=sys.stderr)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        "".join(json.dumps(document, ensure_ascii=False) + "\n" for document in documents), encoding="utf-8"
    )
    print(f"{len(documents)} artigos em {args.out}", file=sys.stderr)
