"""Project knowledge: page-anchored conversion, the citation graph, evidence or nothing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import spec, write
from covener import config
from covener.cli import main
from covener.knowledge.citations import build_graph, extract_citations
from covener.knowledge.convert import Document, build_documents
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
    kids = add(b"")  # the pages object, filled in once the pages exist
    for text in pages:
        stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1")
        content = add(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
        page_ids.append(
            add(
                f"<< /Type /Page /Parent {kids} 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 {font} 0 R >> >> /Contents {content} 0 R >>".encode()
            )
        )
    objects[kids - 1] = (
        f"<< /Type /Pages /Kids [{' '.join(f'{p} 0 R' for p in page_ids)}] /Count {len(page_ids)} >>".encode()
    )
    catalog = add(f"<< /Type /Catalog /Pages {kids} 0 R >>".encode())
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


def test_citations_are_extracted_normalised_and_linked_both_ways() -> None:
    found = extract_citations(LEY)
    assert {(c.target, c.page) for c in found} >= {
        ("Ley 1437 de 2011", 1),
        ("Decreto 1082 de 2015", 1),
        ("Constitución Política", 1),
        ("Sentencia C-123 de 2015", 2),
        ("Resolución 0312 de 2019", 2),
    }
    assert "12" in {c.article for c in found if c.target == "Ley 1437 de 2011"}
    english = extract_citations(
        "## Page 3\nKept under Article 40 of Directive (EU) 2015/849, erased under Regulation (EU) 2016/679."
    )
    assert ("Directive 2015/849", 3, "40") in {(c.target, c.page, c.article) for c in english}
    assert "Regulation 2016/679" in {c.target for c in english}
    # Both directions: what a document cites, and what cites it.
    graph = build_graph(
        [
            Document("ley", "knowledge/ley.md", "knowledge/ley.md", "Ley 1437 de 2011", 2, "a", LEY),
            Document("dec", "knowledge/dec.md", "knowledge/dec.md", "Decreto 1082 de 2015", 1, "b", DECRETO),
        ]
    )
    edges = {(e["source"], e["target"], e["resolved"]) for e in graph.relations_for(["dec"])}
    assert ("dec", "ley", "yes") in edges and ("ley", "dec", "yes") in edges


def test_build_converts_each_source_once_and_writes_the_index(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    make_pdf(tmp_path / "knowledge" / "ley-1437.pdf", ["Ley 1437 de 2011 articulo 1", "Conforme al Decreto 1082"])
    write(tmp_path, "knowledge/decreto-1082.md", DECRETO)
    write(tmp_path, "knowledge/notas/interno.txt", "Nota interna sin citas.")
    assert main(["-C", str(tmp_path), "knowledge", "build", "--no-graph"]) == 0
    converted = tmp_path / "knowledge" / "ley-1437.md"
    assert converted.is_file() and "## Page 2" in converted.read_text()  # pages stay quotable
    index = (tmp_path / "knowledge" / "INDEX.md").read_text()
    assert "| ley-1437 |" in index and "| decreto-1082 |" in index and "| notas/interno |" in index
    citations = (tmp_path / "knowledge" / "CITATIONS.md").read_text()
    assert "## ley-1437 (Ley 1437 de 2011)" in citations
    assert "Cited by:\n- decreto-1082 (pages 1)" in citations
    # Incremental: a second run converts nothing, and a deleted source takes its Markdown with it.
    report = build_documents(tmp_path)
    assert report.converted == [] and len(report.unchanged) == 3
    (tmp_path / "knowledge" / "ley-1437.pdf").unlink()
    report = build_documents(tmp_path)
    assert "knowledge/ley-1437.pdf" in report.removed and not converted.exists()


def test_the_oracle_answers_with_evidence_or_says_nothing(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(repo, "knowledge/ley.md", LEY)
    result = search_knowledge_impl(repo, "silencio administrativo positivo")
    assert result["backend"] == "grep"  # no API key here: the deterministic fallback
    assert result["evidence"][0]["reference"] == "knowledge/ley.md#page-1"
    assert any(r["target"] == "Decreto 1082 de 2015" and r["origin"] == "citation" for r in result["relations"])
    empty = search_knowledge_impl(repo, "criptomonedas cuánticas")
    assert empty["answer"] == "No evidence in the project knowledge." and empty["evidence"] == []
    assert list_sources_impl(repo)[0]["id"] == "ley"
    assert main(["-C", str(repo), "knowledge", "ask", "silencio administrativo", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["evidence"]
    # A spec that cites evidence is checked against the files: a stale reference is a warning.
    spec(repo, "silencio", references="[knowledge/ley.md#page-1, knowledge/missing.md#page-3, Ley 1437 de 2011]")
    missing = [i for i in compute(repo, config.load(repo))[1].warnings if i.code == "spec.reference-missing"]
    assert len(missing) == 1 and "missing.md" in missing[0].message
