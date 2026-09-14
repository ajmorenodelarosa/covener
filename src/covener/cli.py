"""Command-line entry point. Intentionally small: ``init`` and ``status``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .config import ConfigError
from .config import load as load_config
from .init import initialize
from .repo import find_repo_root
from .status import compute, render_json, render_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="covener",
        description="Covener: spec-driven development for AI agent teams. The repository is the source of truth.",
    )
    parser.add_argument("--version", action="version", version=f"covener {__version__}")
    parser.add_argument(
        "-C", "--directory", default=None, help="repository directory (default: detect from the current directory)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="initialise this repository with Covener")
    init_parser.add_argument(
        "--tools",
        default=None,
        help="comma-separated IDE adapters to configure: claude,cursor (default: auto-detect, else both)",
    )
    init_parser.add_argument("--dry-run", action="store_true", help="show what would change without writing")
    init_parser.add_argument(
        "--install-agents",
        action="store_true",
        help="install the default definition for any configured role whose agents/<name>.md is missing",
    )

    knowledge = subparsers.add_parser("knowledge", help="project knowledge: documents agents consult with evidence")
    knowledge_sub = knowledge.add_subparsers(dest="knowledge_command", required=True)
    kb = knowledge_sub.add_parser("build", help="convert knowledge/ sources, index, citation graph, Oracle graph")
    kb.add_argument("--no-graph", action="store_true", help="skip the semantic graph (deterministic layer only)")
    kb.add_argument("--dry-run", action="store_true", help="show what would change without writing")
    ka = knowledge_sub.add_parser("ask", help="ask the Knowledge Oracle from the terminal")
    ka.add_argument("question")
    ka.add_argument("--json", action="store_true", help="machine-readable output")
    subparsers.add_parser("serve", help="run the covener MCP server over stdio (status, search_knowledge)")

    status_parser = subparsers.add_parser(
        "status", help="deterministic overview: backlog, sprints, issues, what is next"
    )
    status_parser.add_argument("--json", action="store_true", help="machine-readable output")
    status_parser.add_argument("-v", "--verbose", action="store_true", help="also list warnings")
    status_parser.add_argument(
        "--strict", action="store_true", help="exit with status 1 when errors are found (for CI)"
    )
    return parser


def _root(args: argparse.Namespace) -> Path:
    if args.directory:
        directory = Path(args.directory)
        if not directory.is_dir():
            raise ConfigError(f"{args.directory} is not a directory")
        return directory.resolve()
    return find_repo_root(Path.cwd())


def cmd_init(args: argparse.Namespace) -> int:
    try:
        root = _root(args)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    tools = [tool.strip() for tool in args.tools.split(",") if tool.strip()] if args.tools else None
    try:
        report = initialize(
            root,
            tools=tools,
            dry_run=args.dry_run,
            install_agents=args.install_agents,
        )
    except (ValueError, ConfigError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(report.render())
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    try:
        root = _root(args)
        config = load_config(root)
        _, report, snapshot = compute(root, config)
    except (ConfigError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(render_json(snapshot) if args.json else render_text(snapshot, verbose=args.verbose))
    if args.strict and report.errors:
        return 1
    return 0


def cmd_knowledge(args: argparse.Namespace) -> int:
    from .knowledge import cli as knowledge_cli

    try:
        root = _root(args)
        if args.knowledge_command == "build":
            return knowledge_cli.build(root, graph=not args.no_graph, dry_run=args.dry_run)
        return knowledge_cli.ask(root, args.question, as_json=args.json)
    except (ConfigError, OSError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def cmd_serve(args: argparse.Namespace) -> int:
    from .mcp_server import serve

    try:
        serve(_root(args))
    except (ConfigError, OSError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "init":
        return cmd_init(args)
    if args.command == "status":
        return cmd_status(args)
    if args.command == "knowledge":
        return cmd_knowledge(args)
    if args.command == "serve":
        return cmd_serve(args)
    parser.print_help()  # pragma: no cover
    return 2  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
