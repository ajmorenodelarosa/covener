"""Deterministic citation graph for legal and regulatory corpora.

Regulatory text is a web of explicit references ("conforme al artículo 12 de la Ley 1437 de
2011"). Extracting them by pattern needs no model, never hallucinates, and answers the two
questions that matter for governance: what does this document rely on, and what depends on it.
Patterns cover Spanish-language public law (Colombia, Spain, Latin America) and common
international forms; unknown references simply stay as text.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field

from .convert import GENERATED_MARK, PAGE_HEADING_RE, Document

# Each pattern yields a normalised id via the named groups (kind, number, year) or (kind, number).
PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?P<kind>Ley(?:\s+Estatutaria|\s+Orgánica)?)\s+(?P<number>\d{1,5})\s+de\s+(?P<year>\d{4})", re.I),
    re.compile(
        r"\b(?P<kind>Decreto(?:\s+Ley|\s+Legislativo|\s+Único|\s+Reglamentario)?)\s+(?P<number>\d{1,5})\s+de\s+(?P<year>\d{4})",
        re.I,
    ),
    re.compile(
        r"\b(?P<kind>Resolución|Acuerdo|Circular(?:\s+Externa)?|Directiva|Ordenanza)\s+(?:N[°ºo.]*\s*)?(?P<number>[\d.-]{1,12})\s+de\s+(?P<year>\d{4})",
        re.I,
    ),
    re.compile(r"\b(?P<kind>Sentencia)\s+(?P<number>(?:C|T|SU|A)-\d{1,5})\s+(?:de|del)\s+(?P<year>\d{4})", re.I),
    re.compile(r"\b(?P<kind>Real\s+Decreto(?:\s+Legislativo|-ley)?)\s+(?P<number>\d{1,5}/\d{4})", re.I),
    re.compile(r"\b(?P<kind>Ley(?:\s+Orgánica)?)\s+(?P<number>\d{1,3}/\d{4})", re.I),
    re.compile(
        r"\b(?P<kind>Reglamento|Directiva|Regulation|Directive)\s+\((?:UE|EU|CE|EC)\)\s+(?:No\.?\s*|n[.º°]\s*)?(?P<number>\d{1,4}/\d{2,4})",
        re.I,
    ),
)
CONSTITUTION_RE = re.compile(r"\bConstituci[oó]n\s+Pol[ií]tica\b", re.I)
ARTICLE_RE = re.compile(r"\b(?:art[ií]culo|art\.)\s*(?P<number>\d{1,4}[A-Za-z]?)", re.I)


def normalise(kind: str, number: str, year: str | None) -> str:
    kind = " ".join(kind.split()).title()
    kind = kind.replace("De ", "de ").replace("Ley-Ley", "Ley")
    ref = f"{kind} {number}"
    return f"{ref} de {year}" if year else ref


@dataclass
class Citation:
    target: str  # normalised norm id, e.g. "Ley 1437 de 2011"
    page: int
    article: str = ""  # article number when the citation names one


@dataclass
class CitationGraph:
    identity: dict[str, str] = field(default_factory=dict)  # doc id -> norm id it is (if detected)
    cites: dict[str, list[Citation]] = field(default_factory=lambda: defaultdict(list))  # doc id -> citations
    resolved: dict[str, str] = field(default_factory=dict)  # norm id -> doc id when the norm is in the corpus

    def cited_by(self, doc_id: str) -> list[tuple[str, int]]:
        norm = self.identity.get(doc_id)
        if not norm:
            return []
        result = []
        for other, citations in self.cites.items():
            if other == doc_id:
                continue
            pages = sorted({c.page for c in citations if c.target == norm})
            result += [(other, page) for page in pages]
        return result

    def relations_for(self, doc_ids: list[str]) -> list[dict[str, str]]:
        """Edges touching any of ``doc_ids``: {source, target, page, resolved}."""
        edges: list[dict[str, str]] = []
        for doc_id in doc_ids:
            seen: set[tuple[str, int]] = set()
            for citation in self.cites.get(doc_id, []):
                key = (citation.target, citation.page)
                if key in seen:
                    continue
                seen.add(key)
                edges.append(
                    {
                        "source": doc_id,
                        "target": self.resolved.get(citation.target, citation.target),
                        "page": str(citation.page),
                        "resolved": "yes" if citation.target in self.resolved else "no",
                    }
                )
            for other, page in self.cited_by(doc_id):
                edges.append({"source": other, "target": doc_id, "page": str(page), "resolved": "yes"})
        return edges


def extract_citations(text: str) -> list[Citation]:
    citations: list[Citation] = []
    page = 1
    for line in text.splitlines():
        heading = PAGE_HEADING_RE.match(line.strip())
        if heading:
            page = int(heading.group(1))
            continue
        for pattern in PATTERNS:
            for match in pattern.finditer(line):
                target = normalise(match.group("kind"), match.group("number"), match.groupdict().get("year"))
                before = line[max(0, match.start() - 40) : match.start()]
                article = ARTICLE_RE.search(before)
                citations.append(Citation(target=target, page=page, article=article.group("number") if article else ""))
        if CONSTITUTION_RE.search(line):
            citations.append(Citation(target="Constitución Política", page=page))
    return citations


def detect_identity(document: Document) -> str:
    """The norm a document *is*: the first pattern match in its title or first lines."""
    head = "\n".join(document.text.splitlines()[:40])
    for candidate in (document.title, head):
        for pattern in PATTERNS:
            match = pattern.search(candidate)
            if match:
                return normalise(match.group("kind"), match.group("number"), match.groupdict().get("year"))
    return ""


def build_graph(documents: list[Document]) -> CitationGraph:
    graph = CitationGraph()
    for doc in documents:
        norm = detect_identity(doc)
        if norm:
            graph.identity[doc.id] = norm
            graph.resolved.setdefault(norm, doc.id)
    for doc in documents:
        own = graph.identity.get(doc.id)
        graph.cites[doc.id] = [c for c in extract_citations(doc.text) if c.target != own]
    return graph


def render_citations(documents: list[Document], graph: CitationGraph) -> str:
    lines = [
        GENERATED_MARK,
        "# Citation graph",
        "",
        "What each document cites and what cites it. Built by pattern, no model.",
        "",
    ]
    for doc in documents:
        norm = graph.identity.get(doc.id)
        lines.append(f"## {doc.id}" + (f" ({norm})" if norm else ""))
        targets: dict[str, list[int]] = defaultdict(list)
        for citation in graph.cites.get(doc.id, []):
            if citation.page not in targets[citation.target]:
                targets[citation.target].append(citation.page)
        if targets:
            lines.append("Cites:")
            for target, pages in sorted(targets.items()):
                where = graph.resolved.get(target)
                link = f" -> {where}" if where else ""
                lines.append(f"- {target}{link} (pages {', '.join(map(str, pages))})")
        cited = graph.cited_by(doc.id)
        if cited:
            lines.append("Cited by:")
            by: dict[str, list[int]] = defaultdict(list)
            for other, page in cited:
                by[other].append(page)
            for other, pages in sorted(by.items()):
                lines.append(f"- {other} (pages {', '.join(map(str, pages))})")
        if not targets and not cited:
            lines.append("No citations detected.")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
