"""The ``covener`` MCP server: the framework's capabilities as tools for the model.

Runs locally over stdio. Same implementation as the CLI, which stays the door for people and CI.
Tools: ``status``, ``search_knowledge``, ``list_knowledge_sources``. Nothing that changes the
repository on the model's behalf.
"""

from __future__ import annotations

import json
from pathlib import Path

from .config import load as load_config
from .knowledge.mcp_server import list_sources_impl, make_oracle
from .status import compute


def mcp_available() -> bool:
    try:
        import mcp.server  # noqa: F401
    except ImportError:
        return False
    return True


def serve(root: Path) -> None:
    try:
        from mcp.server import MCPServer
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise RuntimeError("The MCP server needs the mcp package: pip install 'covener[mcp]'") from exc

    server = MCPServer("covener")
    oracle, backend = make_oracle(root)  # one Oracle for the server's single event loop

    @server.tool()  # type: ignore[untyped-decorator]
    def status(domain: str | None = None) -> str:
        """Deterministic state of this Covener repository as JSON: specs (with their domain folders),
        bugs, tasks, derived backlog, open changes with their state and task progress, done items,
        errors, warnings and the next actions. Pass `domain` (e.g. "billing") to focus on one domain.
        Same data as `covener status --json [--domain ...]`."""
        _, _, snapshot = compute(root, load_config(root), domain)
        return json.dumps(snapshot.to_dict(), ensure_ascii=False)

    @server.tool()  # type: ignore[untyped-decorator]
    async def search_knowledge(question: str) -> str:
        """Ask the project's Knowledge Oracle (regulations, contracts, procedures in knowledge/).
        Returns JSON: answer, relations (graph and citation edges) and evidence with
        knowledge/<file>.md#page-N references to cite in specs and bugs. Never guesses: without
        evidence it says so."""
        result = (await oracle.aask(question)).to_dict()
        result["backend"] = backend
        return json.dumps(result, ensure_ascii=False)

    @server.tool()  # type: ignore[untyped-decorator]
    def list_knowledge_sources() -> str:
        """List the documents in knowledge/ with id, title and page count (JSON)."""
        return json.dumps(list_sources_impl(root), ensure_ascii=False)

    server.run(transport="stdio")
