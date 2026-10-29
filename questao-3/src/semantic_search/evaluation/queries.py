"""Geração das consultas de avaliação: um LLM escreve as consultas e um juiz rotula a relevância.

Uso, na pasta da questão: uv run --env-file .env semantic-search-queries

1. Sorteia artigos do corpus e um parágrafo longo de cada um.
2. O gerador escreve, a partir do título, do resumo e do parágrafo, três consultas por artigo, em inglês
   e em português: pelo nome (com o termo próprio do artigo), por paráfrase (sem nenhum termo próprio) e
   por um detalhe que só o parágrafo responde, com a frase do parágrafo que responde.
3. O gerador propõe consultas por tema, a partir dos títulos e resumos de todo o corpus.
4. O juiz lê os 100 resumos para cada consulta e diz quais artigos são relevantes. Sem isso, os rótulos
   cobririam só o artigo de origem, e a cobertura (recall) da busca não teria como ser medida.

O LLM não é determinístico: o arquivo gerado é a fonte da verdade, revisado e versionado no repositório,
e este script é o registro de como ele foi feito.
"""

import argparse
import json
import os
import random
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel, Field

from semantic_search.corpus import Document, load_documents
from semantic_search.evaluation.metrics import contains_quote

# Parágrafo mais curto que isso ("Results are in Table 2.") não sustenta uma pergunta de detalhe.
MIN_PASSAGE_WORDS = 60


@dataclass(frozen=True, slots=True, kw_only=True)
class Passage:
    """Um parágrafo do corpo de um artigo, de onde sai a consulta de detalhe."""

    paper_id: str
    section: str
    # Posição do parágrafo entre os parágrafos de todo o corpo do artigo, a partir de 0.
    paragraph_index: int
    text: str


def choose_passages(documents: Sequence[Document], *, count: int, seed: int) -> list[Passage]:
    """Um parágrafo longo de cada artigo sorteado; artigo sem parágrafo longo fica de fora.

    A mesma semente dá os mesmos trechos, para que o conjunto possa ser refeito.
    """
    rng = random.Random(seed)
    papers = rng.sample(sorted(documents, key=lambda document: document.id), count)
    passages = []
    for document in papers:
        paragraphs = [(section.heading, paragraph) for section in document.sections for paragraph in section.paragraphs]
        eligible = [index for index, (_, text) in enumerate(paragraphs) if len(text.split()) >= MIN_PASSAGE_WORDS]
        if not eligible:
            continue
        index = rng.choice(eligible)
        section, text = paragraphs[index]
        passages.append(Passage(paper_id=document.id, section=section, paragraph_index=index, text=text))
    return passages


def quote_in_passage(quote: str, passage: Passage) -> bool:
    """A citação foi copiada do parágrafo, sem reescrita; só o espaço entre as palavras pode mudar."""
    return contains_quote(passage.text, quote)


def label_relevance(*, judged: set[str], source: str | None) -> tuple[list[str], bool]:
    """Artigos relevantes da consulta e se ela precisa de revisão.

    O artigo de origem é sempre relevante: a consulta foi escrita a partir dele. Se o juiz discorda, a
    consulta ficou vaga ou o juiz errou, e ela é marcada para revisão. Um tema sem nenhum artigo
    relevante também é marcado: não mede nada.
    """
    relevant = judged | ({source} if source else set())
    needs_review = (source is not None and source not in judged) or not relevant
    return sorted(relevant), needs_review


class Bilingual(BaseModel):
    en: str = Field(description="A consulta em inglês.")
    pt: str = Field(description="A mesma consulta em português do Brasil, natural, não traduzida palavra por palavra.")


class PaperQueries(BaseModel):
    named: Bilingual = Field(description="Consulta que usa o nome próprio ou o termo mais específico do artigo.")
    paraphrase: Bilingual = Field(
        description="Consulta sobre a contribuição principal sem nenhum termo próprio do artigo."
    )
    detail: Bilingual = Field(description="Pergunta que só o trecho responde, compreensível sem o artigo.")
    evidence: str = Field(description="A frase do trecho que responde a pergunta de detalhe, copiada sem mudar nada.")


class TopicQueries(BaseModel):
    topics: list[Bilingual]


class Judgment(BaseModel):
    reasoning: str = Field(description="Por que cada artigo marcado é relevante, em uma frase por artigo.")
    relevant_ids: list[str] = Field(description="Ids dos artigos relevantes; lista vazia se nenhum for.")


_QUERY_RULES = """\
Rules for every query:
- Write it as a researcher would ask a search engine over recent NLP papers: a question or a natural \
descriptive phrase of 5 to 20 words, not a list of keywords.
- The searcher has not read the paper: never write "this paper", "the authors" or "the proposed method".
- The Portuguese version is natural Brazilian Portuguese: translate every common word ("false alarms" is \
"falsos alarmes", "checks" is "verificações", "language model" is "modelo de linguagem", "retrieval" is \
"recuperação"). Keep in English only proper names (of methods, datasets, benchmarks, models) and the few \
terms Brazilian researchers do not translate: LLM, fine-tuning, embedding, benchmark, prompt, token."""

PAPER_PROMPT = f"""\
You write search queries to evaluate a semantic search engine over recent NLP papers from arXiv.

Given a paper's title, abstract and one passage from its body, write three queries:

1. named: a query that uses the paper's own name for its method, system, dataset or benchmark. If the \
paper names nothing, use its most specific technical term.
2. paraphrase: a query about the paper's main contribution that uses none of the paper's own names or \
distinctive terms from the title and abstract. Describe the idea in other words, as someone who does not \
know what the method is called would.
3. detail: a question that the passage answers and the abstract does not, specific enough to make sense \
on its own (mention the topic, not "the experiment"). Copy into "evidence" the sentence or sentences of \
the passage that answer it, exactly as written.

{_QUERY_RULES}"""

TOPIC_PROMPT = f"""\
You write search queries to evaluate a semantic search engine over recent NLP papers from arXiv.

Below are the titles and abstracts of every paper in the collection. Write {{count}} topical queries, \
each about a research theme that 2 to 8 of these papers address. Spread them across different themes. \
Do not name a specific paper or method.

{_QUERY_RULES}"""

JUDGE_PROMPT = """\
You judge relevance for a search engine over recent NLP papers from arXiv.

Below are the titles and abstracts of every paper in the collection, followed by one search query. List \
the ids of the papers a researcher issuing this query would want in the results: papers that \
substantially address what the query asks. A paper that only shares a word or a broad area with the \
query is not relevant. A query about a specific detail is relevant to the paper that reports that detail, \
even if the abstract does not mention it, when the abstract makes clear the paper covers that subject. \
Explain briefly before giving the ids."""


def _collection(documents: Sequence[Document]) -> str:
    return "\n\n".join(f"[{document.id}] {document.title}\n{document.abstract}" for document in documents)


def _parse[T: BaseModel](client: OpenAI, model: str, system: str, user: str, schema: type[T]) -> T:
    completion = client.chat.completions.parse(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        response_format=schema,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise ValueError(f"o modelo não devolveu {schema.__name__}")
    return parsed


def generate_paper_queries(client: OpenAI, model: str, document: Document, passage: Passage) -> PaperQueries | None:
    """As três consultas do artigo; None quando a citação da consulta de detalhe não é cópia do trecho."""
    user = (
        f"Title: {document.title}\n\nAbstract: {document.abstract}\n\n"
        f'Passage (section "{passage.section}"):\n{passage.text}'
    )
    for _ in range(2):
        queries = _parse(client, model, PAPER_PROMPT, user, PaperQueries)
        if quote_in_passage(queries.evidence, passage):
            return queries
    return None


def judge(client: OpenAI, model: str, collection: str, query: str) -> Judgment:
    # O corpus vem antes da consulta: o começo da entrada é igual em toda chamada, e o cache de prompt
    # da OpenAI cobra esse começo com desconto a partir da segunda consulta.
    return _parse(client, model, JUDGE_PROMPT, f"{collection}\n\nQuery: {query}", Judgment)


QueryType = Literal["named", "paraphrase", "detail", "topic"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera as consultas de avaliação da busca.")
    parser.add_argument("--corpus", type=Path, default=Path("data/corpus.jsonl"))
    parser.add_argument("--papers", type=int, default=30, help="artigos que geram consultas próprias")
    parser.add_argument("--topics", type=int, default=10, help="consultas por tema")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", type=Path, default=Path("evals/queries.json"))
    args = parser.parse_args()

    query_model = os.environ.get("EVAL_QUERY_MODEL", "gpt-5.4-mini")
    judge_model = os.environ.get("EVAL_JUDGE_MODEL", "gpt-5.4")
    client = OpenAI()
    documents = load_documents(args.corpus)
    by_id = {document.id: document for document in documents}
    collection = _collection(documents)

    drafts: list[tuple[QueryType, Bilingual, str | None, dict[str, object] | None]] = []
    for passage in choose_passages(documents, count=args.papers, seed=args.seed):
        queries = generate_paper_queries(client, query_model, by_id[passage.paper_id], passage)
        if queries is None:
            print(f"{passage.paper_id}: citação reescrita duas vezes, artigo pulado", file=sys.stderr)
            continue
        evidence = {
            "paper": passage.paper_id,
            "section": passage.section,
            "paragraph": passage.paragraph_index,
            "quote": " ".join(queries.evidence.split()),
        }
        drafts += [
            ("named", queries.named, passage.paper_id, None),
            ("paraphrase", queries.paraphrase, passage.paper_id, None),
            ("detail", queries.detail, passage.paper_id, evidence),
        ]
        print(f"{passage.paper_id}: 3 consultas", file=sys.stderr)
    if args.topics:
        topics = _parse(client, query_model, TOPIC_PROMPT.format(count=args.topics), collection, TopicQueries)
        drafts += [("topic", topic, None, None) for topic in topics.topics[: args.topics]]

    records = []
    for number, (query_type, text, source, draft_evidence) in enumerate(drafts, 1):
        # Os rótulos valem para as duas línguas: o juiz lê a versão em inglês, a língua do corpus.
        judgment = judge(client, judge_model, collection, text.en)
        known = {paper_id for paper_id in judgment.relevant_ids if paper_id in by_id}
        relevant, needs_review = label_relevance(judged=known, source=source)
        records.append(
            {
                "id": f"q{number:03d}",
                "type": query_type,
                "query": {"en": text.en, "pt": text.pt},
                "relevant": relevant,
                "source": source,
                "evidence": draft_evidence,
                "needs_review": needs_review,
                "judge_reasoning": judgment.reasoning,
            }
        )
        print(
            f"q{number:03d} {query_type}: {len(relevant)} relevantes{' (revisar)' if needs_review else ''}",
            file=sys.stderr,
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    metadata = {"query_model": query_model, "judge_model": judge_model, "seed": args.seed, "corpus": str(args.corpus)}
    args.out.write_text(
        json.dumps({"metadata": metadata, "queries": records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{len(records)} consultas em {args.out}", file=sys.stderr)
