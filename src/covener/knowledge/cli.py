"""``covener knowledge``: build the project knowledge and ask it from the terminal."""

from __future__ import annotations

import json
from pathlib import Path

from .citations import build_graph, render_citations
from .convert import CITATIONS_FILE, INDEX_FILE, KNOWLEDGE_DIR, STATE_DIR, build_documents, render_index

GITIGNORE_LINE = ".covener/knowledge/"


def build(root: Path, graph: bool, dry_run: bool) -> int:
    knowledge = root / KNOWLEDGE_DIR
    if not knowledge.is_dir():
        if not dry_run:
            knowledge.mkdir(parents=True)
        print(f"Created {KNOWLEDGE_DIR}/. Put PDF, Markdown or text documents there and run this again.")
        return 0
    report = build_documents(root, dry_run=dry_run)
    citation_graph = build_graph(report.documents)
    if not dry_run:
        (knowledge / INDEX_FILE).write_text(render_index(report.documents), encoding="utf-8")
        (knowledge / CITATIONS_FILE).write_text(render_citations(report.documents, citation_graph), encoding="utf-8")
        gitignore = root / ".gitignore"
        existing = gitignore.read_text(encoding="utf-8") if gitignore.is_file() else ""
        if GITIGNORE_LINE not in existing.splitlines():
            gitignore.write_text(
                existing.rstrip("\n") + ("\n" if existing else "") + GITIGNORE_LINE + "\n", encoding="utf-8"
            )
    print(f"Covener knowledge{' (dry run)' if dry_run else ''}")
    counts = f"converted: {len(report.converted)}  unchanged: {len(report.unchanged)}  removed: {len(report.removed)}"
    print(f"  Documents: {len(report.documents)}  {counts}")
    edges = sum(len(v) for v in citation_graph.cites.values())
    print(f"  Citations: {edges} references, {len(citation_graph.resolved)} resolved to documents in the corpus")
    for item in report.converted:
        print(f"  + {item}")
    for item in report.removed:
        print(f"  - {item}")
    for item in report.skipped:
        print(f"  ! {item}")
    if graph and not dry_run and report.documents:
        from .oracle import LightRAGOracle

        try:
            oracle = LightRAGOracle(root, report.documents)
            oracle.build(report.documents)
            print(f"  Oracle: graph updated in {STATE_DIR.as_posix()}/graph")
        except RuntimeError as exc:
            report.notes.append(f"Oracle graph not built: {exc}. The deterministic layer still works.")
    for note in report.notes:
        print(f"  - {note}")
    return 0


def ask(root: Path, question: str, as_json: bool) -> int:
    from .mcp_server import search_knowledge_impl

    result = search_knowledge_impl(root, question)
    if as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    print(result["answer"])
    if result["evidence"]:
        print("\nEvidence")
        for item in result["evidence"]:
            print(f"  - {item['reference']}: {item['excerpt'][:160]}")
    if result["relations"]:
        print("\nRelations")
        for rel in result["relations"][:20]:
            print(f"  - {rel.get('source')} -> {rel.get('target')} ({rel.get('origin')})")
    print(f"\n(backend: {result['backend']})")
    return 0
