"""Knowledge capabilities shared by the CLI (``covener knowledge ask``) and the ``covener`` MCP
server: one dynamic capability, ``search_knowledge``, that returns an answer, the relations it
used and the evidence, so an agent can cite ``knowledge/<file>.md#page-N`` and a reviewer can
verify it. The database is never exposed.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .convert import build_documents
from .oracle import GrepOracle, LightRAGOracle, Oracle


def make_oracle(root: Path) -> tuple[Oracle, str]:
    documents = build_documents(root, dry_run=True).documents
    try:
        import lightrag  # noqa: F401

        if os.environ.get("ANTHROPIC_API_KEY") and os.environ.get("VOYAGE_API_KEY"):
            return LightRAGOracle(root, documents), "lightrag"
    except ImportError:
        pass
    return GrepOracle(documents), "grep"


def search_knowledge_impl(root: Path, question: str) -> dict[str, Any]:
    oracle, backend = make_oracle(root)
    result = oracle.ask(question).to_dict()
    result["backend"] = backend
    return result


def list_sources_impl(root: Path) -> list[dict[str, Any]]:
    return [
        {"id": d.id, "title": d.title, "pages": d.pages, "markdown": d.markdown}
        for d in build_documents(root, dry_run=True).documents
    ]
