"""The Knowledge Oracle: answer + relations + evidence, over a replaceable backend.

The interface is two operations. The first backend is LightRAG (graph + vectors on local files,
no server) with a frontier model for extraction and answers and Voyage embeddings for retrieval.
Both are chosen for quality on multilingual legal text; keys come from the environment:

    ANTHROPIC_API_KEY   required
    VOYAGE_API_KEY      required
    COVENER_LLM_MODEL   default claude-sonnet-5
    COVENER_EMBED_MODEL default voyage-4-large (voyage-law-2 is tuned for legal text)

The citation graph is always merged into the relations, so "what cites what" never depends on
the model.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol

from .citations import CitationGraph, build_graph
from .convert import PAGE_HEADING_RE, STATE_DIR, Document

GRAPH_DIR = STATE_DIR / "graph"
DEFAULT_LLM_MODEL = "claude-sonnet-5"
DEFAULT_EMBED_MODEL = "voyage-4-large"
EMBED_DIM = 1024

SYSTEM_PROMPT = (
    "You are the Knowledge Oracle of a software project. Answer only from the retrieved context. "
    "Quote the exact wording for legal or regulatory statements and name the document and page "
    "in the form [file#page-N]. If the context does not contain the answer, say exactly: "
    "'No evidence in the project knowledge.' Answer in the language of the question."
)


@dataclass
class Evidence:
    document: str  # document id
    reference: str  # knowledge/<file>.md#page-N
    excerpt: str


@dataclass
class Answer:
    question: str
    answer: str
    relations: list[dict[str, str]] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Oracle(Protocol):
    def ask(self, question: str) -> Answer: ...
    async def aask(self, question: str) -> Answer: ...


def split_pages(excerpt: str, limit: int = 6) -> list[tuple[int, str]]:
    """Split a retrieved chunk by its ``## Page N`` headings so every piece of evidence has a page."""
    pages: list[tuple[int, list[str]]] = [(1, [])]
    for line in excerpt.splitlines():
        heading = PAGE_HEADING_RE.match(line.strip())
        if heading:
            pages.append((int(heading.group(1)), []))
        elif line.strip() and not line.startswith("# ") and not line.startswith("<!--"):
            pages[-1][1].append(line.rstrip())
    result = [(page, "\n".join(lines).strip()) for page, lines in pages if lines]
    return result[:limit]


class LightRAGOracle:
    """Graph + vector retrieval on local files (NetworkX and nano-vectordb), no server.

    LightRAG binds its worker queues to the event loop that initialised it, so one instance is
    created per running loop: the sync ``build``/``ask`` wrappers each run in their own loop, and a
    long-running server (the MCP process) keeps one instance for its single loop.
    """

    def __init__(self, root: Path, documents: list[Document]) -> None:
        self.root = root
        self.documents = {doc.markdown: doc for doc in documents}
        self.by_id = {doc.id: doc for doc in documents}
        self.graph: CitationGraph = build_graph(documents)
        self._rag: Any = None
        self._loop: Any = None

    # --- backend wiring ------------------------------------------------------------------
    @staticmethod
    def check_environment() -> None:
        try:
            import lightrag  # noqa: F401
        except ImportError as exc:  # pragma: no cover - depends on the environment
            raise RuntimeError("The Oracle needs its extras: pip install 'covener[oracle]'") from exc
        for key in ("ANTHROPIC_API_KEY", "VOYAGE_API_KEY"):
            if not os.environ.get(key):
                raise RuntimeError(f"{key} is not set; the Oracle needs it")

    def _functions(self) -> tuple[Any, Any, str]:
        """The model functions LightRAG calls: (llm, embed, embedding model name)."""
        llm_model = os.environ.get("COVENER_LLM_MODEL", DEFAULT_LLM_MODEL)
        embed_model = os.environ.get("COVENER_EMBED_MODEL", DEFAULT_EMBED_MODEL)

        async def llm(
            prompt: str,
            system_prompt: str | None = None,
            history_messages: list[dict[str, str]] | None = None,
            **_: Any,
        ) -> str:
            import anthropic

            client = anthropic.AsyncAnthropic()
            messages: list[Any] = list(history_messages or []) + [{"role": "user", "content": prompt}]
            response = await client.messages.create(
                model=llm_model, max_tokens=8000, system=system_prompt or "", messages=messages
            )
            return "".join(str(getattr(block, "text", "")) for block in response.content if block.type == "text")

        async def embed(texts: list[str]) -> Any:
            import numpy as np
            import voyageai

            client: Any = voyageai.AsyncClient()  # type: ignore[attr-defined]
            vectors: list[Any] = []
            for start in range(0, len(texts), 64):
                result = await client.embed(texts[start : start + 64], model=embed_model, input_type="document")
                vectors.extend(result.embeddings)
            return np.array(vectors, dtype=np.float32)

        return llm, embed, embed_model

    async def _rag_for_loop(self) -> Any:
        loop = asyncio.get_running_loop()
        if self._rag is not None and self._loop is loop:
            return self._rag
        from lightrag import LightRAG
        from lightrag.kg.shared_storage import initialize_pipeline_status
        from lightrag.utils import EmbeddingFunc

        self.check_environment()
        llm, embed, embed_model = self._functions()
        working_dir = self.root / GRAPH_DIR
        working_dir.mkdir(parents=True, exist_ok=True)
        rag = LightRAG(
            working_dir=str(working_dir),
            llm_model_func=llm,
            embedding_func=EmbeddingFunc(
                embedding_dim=EMBED_DIM, max_token_size=32000, func=embed, model_name=embed_model
            ),
        )
        await rag.initialize_storages()
        await initialize_pipeline_status()
        self._rag, self._loop = rag, loop
        return rag

    def _document_for(self, file_path: str | None, excerpt: str) -> Document | None:
        """LightRAG keeps only the file name; match it, then confirm (or fall back) by content."""
        candidates = list(self.documents.values())
        if file_path:
            name = file_path.replace("\\", "/").rsplit("/", 1)[-1]
            named = [d for d in candidates if d.markdown.rsplit("/", 1)[-1] == name]
            if len(named) == 1:
                return named[0]
            candidates = named or candidates
        needle = next((line.strip() for line in excerpt.splitlines() if len(line.strip()) > 30), "")
        for doc in candidates:
            if needle and needle in doc.text:
                return doc
        return candidates[0] if len(candidates) == 1 else None

    # --- operations --------------------------------------------------------------------------
    async def abuild(self, documents: list[Document]) -> None:
        """Index changed documents only; unchanged content is skipped by hash."""
        rag = await self._rag_for_loop()
        state_path = self.root / GRAPH_DIR / "indexed.json"
        indexed: dict[str, str] = {}
        if state_path.is_file():
            with contextlib.suppress(ValueError):
                indexed = json.loads(state_path.read_text(encoding="utf-8"))
        stale = [doc for doc in documents if indexed.get(doc.id) != doc.sha256]
        gone = [doc_id for doc_id in indexed if doc_id not in {d.id for d in documents}]
        for doc_id in gone + [d.id for d in stale if d.id in indexed]:
            with contextlib.suppress(Exception):  # a missing id is not a failure
                await rag.adelete_by_doc_id(f"doc-{doc_id}")
        if stale:
            await rag.ainsert(
                input=[d.text for d in stale],
                ids=[f"doc-{d.id}" for d in stale],
                file_paths=[d.markdown for d in stale],
            )
        for doc in stale:
            indexed[doc.id] = doc.sha256
        for doc_id in gone:
            indexed.pop(doc_id, None)
        state_path.write_text(json.dumps(indexed, indent=2) + "\n", encoding="utf-8")

    async def aask(self, question: str) -> Answer:
        from lightrag import QueryParam

        rag = await self._rag_for_loop()
        param = QueryParam(mode="mix", include_references=True)
        result = await rag.aquery_llm(question, param=param, system_prompt=SYSTEM_PROMPT)
        content = ""
        llm_response = result.get("llm_response") if isinstance(result, dict) else None
        if isinstance(llm_response, dict):
            content = str(llm_response.get("content") or "")
        data = result.get("data", {}) if isinstance(result, dict) else {}
        by_reference = {
            str(ref.get("reference_id")): str(ref.get("file_path", "")) for ref in data.get("references", []) or []
        }
        evidence: list[Evidence] = []
        touched: list[str] = []
        for chunk in data.get("chunks", []) or []:
            excerpt = str(chunk.get("content", "")).strip()
            doc = self._document_for(by_reference.get(str(chunk.get("reference_id"))), excerpt)
            if doc is None:
                continue
            for page, text in split_pages(excerpt):
                evidence.append(Evidence(document=doc.id, reference=doc.anchor(page), excerpt=text[:600]))
            if doc.id not in touched:
                touched.append(doc.id)
        relations: list[dict[str, str]] = []
        for rel in data.get("relationships", []) or []:
            relations.append(
                {
                    "source": str(rel.get("src_id", rel.get("source", ""))),
                    "target": str(rel.get("tgt_id", rel.get("target", ""))),
                    "description": str(rel.get("description", ""))[:300],
                    "origin": "graph",
                }
            )
        for edge in self.graph.relations_for(touched):
            relations.append({**edge, "origin": "citation"})
        return Answer(
            question=question,
            answer=content or "No evidence in the project knowledge.",
            relations=relations,
            evidence=evidence,
        )

    def build(self, documents: list[Document]) -> None:
        self._rag = None
        asyncio.run(self.abuild(documents))
        self._rag = None

    def ask(self, question: str) -> Answer:
        self._rag = None
        try:
            return asyncio.run(self.aask(question))
        finally:
            self._rag = None


class GrepOracle:
    """No-model fallback: literal search over the Markdown plus the citation graph.

    Used when the Oracle extras or keys are absent, so ``search_knowledge`` always answers with
    evidence, never with a guess.
    """

    def __init__(self, documents: list[Document]) -> None:
        self.documents = documents
        self.graph = build_graph(documents)

    def build(self, documents: list[Document]) -> None:
        self.documents = documents
        self.graph = build_graph(documents)

    async def aask(self, question: str) -> Answer:
        return self.ask(question)

    def ask(self, question: str) -> Answer:
        words = [w.lower() for w in question.split() if len(w) > 3]
        evidence: list[Evidence] = []
        touched: list[str] = []
        for doc in self.documents:
            page = 1
            for line in doc.text.splitlines():
                heading = PAGE_HEADING_RE.match(line.strip())
                if heading:
                    page = int(heading.group(1))
                    continue
                lowered = line.lower()
                if words and sum(w in lowered for w in words) >= max(1, len(words) // 2):
                    evidence.append(Evidence(document=doc.id, reference=doc.anchor(page), excerpt=line.strip()[:600]))
                    if doc.id not in touched:
                        touched.append(doc.id)
                if len(evidence) >= 20:
                    break
        answer = (
            "No evidence in the project knowledge."
            if not evidence
            else ("Literal matches only (no semantic Oracle configured); read the evidence:")
        )
        return Answer(
            question=question,
            answer=answer,
            relations=[{**e, "origin": "citation"} for e in self.graph.relations_for(touched)],
            evidence=evidence,
        )
