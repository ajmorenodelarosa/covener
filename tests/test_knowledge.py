"""Project knowledge: deterministic conversion, citation graph, fallback Oracle, MCP tool, CLI."""

from __future__ import annotations

import json
from pathlib import Path

from conftest import spec, write
from covener import config
from covener.cli import main
from covener.knowledge.citations import build_graph, extract_citations
from covener.knowledge.convert import build_documents
from covener.knowledge.mcp_server import list_sources_impl, search_knowledge_impl
from covener.status import compute

LEY = """<!-- x -->
# Ley 1437 de 2011

## Page 1

Código de Procedimiento Administrativo. Conforme al artículo 12 de la Ley 1437 de 2011 y a la
Constitución Política, el silencio administrativo positivo opera en los términos del Decreto 1082 de 2015.

## Page 2

Véase la Sentencia C-123 de 2015 y la Resolución 0312 de 2019.
"""

DECRETO = """# Decreto 1082 de 2015

## Page 1

Reglamenta la contratación pública. Aplica el artículo 5 de la Ley 1437 de 2011.
"""


def make_pdf(path: Path, pages: list[str]) -> None:
    """A minimal valid PDF with one text object per page, enough for pypdf.extract_text."""
    objects: list[bytes] = []

    def add(obj: bytes) -> int:
        objects.append(obj)
        return len(objects)

    font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_ids = []
    kids_placeholder = add(b"")  # pages object, filled later
    for text in pages:
        stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1")
        content = add(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
        page = add(
            f"<< /Type /Page /Parent {kids_placeholder} 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font} 0 R >> >> /Contents {content} 0 R >>".encode()
        )
        page_ids.append(page)
    objects[kids_placeholder - 1] = (
        f"<< /Type /Pages /Kids [{' '.join(f'{p} 0 R' for p in page_ids)}] /Count {len(page_ids)} >>".encode()
    )
    catalog = add(f"<< /Type /Catalog /Pages {kids_placeholder} 0 R >>".encode())
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root {catalog} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(out))


def test_citations_are_extracted_normalised_and_resolved() -> None:
    found = extract_citations(LEY)
    targets = {(c.target, c.page) for c in found}
    assert ("Ley 1437 de 2011", 1) in targets
    assert ("Decreto 1082 de 2015", 1) in targets
    assert ("Constitución Política", 1) in targets
    assert ("Sentencia C-123 de 2015", 2) in targets
    assert ("Resolución 0312 de 2019", 2) in targets
    assert "12" in {c.article for c in found if c.target == "Ley 1437 de 2011"}
    english = extract_citations(
        "## Page 3\nKept under Article 40 of Directive (EU) 2015/849, erased under Regulation (EU) 2016/679."
    )
    assert ("Directive 2015/849", 3, "40") in {(c.target, c.page, c.article) for c in english}
    assert "Regulation 2016/679" in {c.target for c in english}


def test_build_converts_pdfs_incrementally_and_writes_index_and_graph(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    make_pdf(
        tmp_path / "knowledge" / "ley-1437.pdf", ["Ley 1437 de 2011 articulo 1", "Conforme al Decreto 1082 de 2015"]
    )
    write(tmp_path, "knowledge/decreto-1082.md", DECRETO)
    write(tmp_path, "knowledge/notas/interno.txt", "Nota interna sin citas.")
    assert main(["-C", str(tmp_path), "knowledge", "build", "--no-graph"]) == 0
    converted = tmp_path / "knowledge" / "ley-1437.md"
    assert converted.is_file() and "## Page 2" in converted.read_text()
    index = (tmp_path / "knowledge" / "INDEX.md").read_text()
    assert "| ley-1437 |" in index and "| decreto-1082 |" in index and "| notas/interno |" in index
    citations = (tmp_path / "knowledge" / "CITATIONS.md").read_text()
    assert "## ley-1437 (Ley 1437 de 2011)" in citations
    assert "- Decreto 1082 de 2015 -> decreto-1082 (pages 2)" in citations
    assert "Cited by:\n- decreto-1082 (pages 1)" in citations
    assert ".covener/knowledge/" in (tmp_path / ".gitignore").read_text()
    # Second run: nothing reconverted; a deleted PDF removes its generated Markdown.
    report = build_documents(tmp_path)
    assert report.converted == [] and len(report.unchanged) == 3
    (tmp_path / "knowledge" / "ley-1437.pdf").unlink()
    report = build_documents(tmp_path)
    assert "knowledge/ley-1437.pdf" in report.removed and not converted.exists()


def test_graph_relations_touch_both_directions() -> None:
    from covener.knowledge.convert import Document

    docs = [
        Document(
            id="ley",
            source="knowledge/ley.md",
            markdown="knowledge/ley.md",
            title="Ley 1437 de 2011",
            pages=2,
            sha256="a",
            text=LEY,
        ),
        Document(
            id="dec",
            source="knowledge/dec.md",
            markdown="knowledge/dec.md",
            title="Decreto 1082 de 2015",
            pages=1,
            sha256="b",
            text=DECRETO,
        ),
    ]
    graph = build_graph(docs)
    assert graph.identity == {"ley": "Ley 1437 de 2011", "dec": "Decreto 1082 de 2015"}
    edges = {(e["source"], e["target"], e["resolved"]) for e in graph.relations_for(["dec"])}
    assert ("dec", "ley", "yes") in edges and ("ley", "dec", "yes") in edges


def test_fallback_oracle_answers_with_evidence_never_guesses(tmp_path: Path) -> None:
    write(tmp_path, "knowledge/ley.md", LEY)
    result = search_knowledge_impl(tmp_path, "silencio administrativo positivo")
    assert result["backend"] == "grep"
    assert result["evidence"][0]["reference"] == "knowledge/ley.md#page-1"
    assert any(r["target"] == "Decreto 1082 de 2015" and r["origin"] == "citation" for r in result["relations"])
    empty = search_knowledge_impl(tmp_path, "criptomonedas cuánticas")
    assert empty["answer"] == "No evidence in the project knowledge." and empty["evidence"] == []
    assert list_sources_impl(tmp_path)[0]["id"] == "ley"


def test_references_field_is_validated(repo: Path) -> None:
    write(repo, "knowledge/ley.md", LEY)
    spec(repo, "silencio", references="[knowledge/ley.md#page-1, knowledge/missing.md#page-3, Ley 1437 de 2011]")
    _, report, _ = compute(repo, config.load(repo))
    missing = [i for i in report.warnings if i.code == "spec.reference-missing"]
    assert len(missing) == 1 and "missing.md" in missing[0].message


def test_knowledge_ask_cli(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    write(tmp_path, "knowledge/ley.md", LEY)
    assert main(["-C", str(tmp_path), "knowledge", "ask", "silencio administrativo", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["evidence"]
    assert main(["-C", str(tmp_path), "knowledge", "build", "--dry-run"]) == 0
    assert not (tmp_path / "knowledge" / "INDEX.md").exists()
