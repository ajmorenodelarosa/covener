"""Project Knowledge: domain documents (regulations, contracts, procedures) that agents can
consult with traceable evidence.

Two layers, both optional and outside the Covener core:

* deterministic: ``knowledge/`` sources are converted to Markdown with page anchors, indexed in
  ``knowledge/INDEX.md``, and linked by a citation graph (``knowledge/CITATIONS.md``). No model,
  no network. ``pip install covener[knowledge]``.
* semantic (the Knowledge Oracle): a knowledge graph over the same Markdown, built with a
  frontier model and queried through one MCP tool, ``search_knowledge``, that returns an answer,
  the relations it used and the evidence, page by page. ``pip install covener[oracle]``.
"""
