"""Unit tests for RAG chunking + the IngestDocument use case — no DB, no network."""

import uuid

import pytest

from app.application.documents.ingest import EmptyDocumentError, IngestDocument
from app.domain.documents.chunking import chunk_markdown
from app.domain.documents.entities import Document

# asyncio_mode="auto" (pyproject) runs the async tests; no module-level mark needed since this module
# mixes sync (chunking) and async (use case) tests.

# --- chunking ----------------------------------------------------------------


def test_empty_text_yields_no_chunks():
    assert chunk_markdown("") == []
    assert chunk_markdown("   \n  \n") == []


def test_short_text_is_one_chunk_without_breadcrumb():
    out = chunk_markdown("just a short runbook line", chunk_size=1000)
    assert out == ["just a short runbook line"]


def test_headings_become_breadcrumbs():
    text = "# GCM\n## OOM\nRestart the service and raise memory."
    out = chunk_markdown(text, chunk_size=1000)
    assert len(out) == 1
    assert out[0].startswith("[GCM > OOM]\n")
    assert "Restart the service" in out[0]


def test_long_text_splits_with_overlap():
    body = "\n".join(f"line {i} with some words" for i in range(200))
    out = chunk_markdown(body, chunk_size=400, overlap=80)
    assert len(out) > 1
    # Consecutive chunks share overlapping tail/head content.
    first_tail = out[0].splitlines()[-1]
    assert first_tail in out[1]


def test_nested_heading_scope_pops_deeper_levels():
    text = "# A\n## B\ncontent b\n# C\ncontent c"
    out = chunk_markdown(text, chunk_size=1000)
    # The last chunk's breadcrumb should be just "C" (B popped when C opened at level 1).
    assert out[-1].startswith("[C]\n")


# --- ingest use case ---------------------------------------------------------


class FakeEmbedder:
    def __init__(self):
        self.seen: list[str] = []

    async def embed_documents(self, texts):
        self.seen = list(texts)
        return [[float(i), 0.1, 0.2] for i, _ in enumerate(texts)]

    async def embed_query(self, text):
        return [0.0, 0.1, 0.2]


class FakeDocRepo:
    def __init__(self):
        self.added: list = []

    async def add(self, document: Document, chunks):
        document.id = uuid.uuid4()
        self.added.append((document, list(chunks)))
        return document

    async def list(self):
        return []


class FakeUoW:
    def __init__(self):
        self.commits = 0

    async def commit(self):
        self.commits += 1


async def test_ingest_chunks_embeds_and_stores():
    embedder, repo, uow = FakeEmbedder(), FakeDocRepo(), FakeUoW()
    usecase = IngestDocument(documents=repo, embedder=embedder, uow=uow, chunk_size=200, overlap=40)
    content = "# GCM Runbook\n" + "\n".join(f"step {i} do the thing" for i in range(60))

    document, n_chunks = await usecase.execute(
        title="GCM Runbook", source_type="runbook", service="GCM", tags=["oom"], content=content
    )

    assert n_chunks > 1
    stored_doc, stored_chunks = repo.added[0]
    assert stored_doc.source_type == "runbook"
    assert stored_doc.service == "GCM"
    assert len(stored_chunks) == n_chunks
    assert stored_chunks[0].index == 0
    assert len(embedder.seen) == n_chunks  # one embedding per chunk
    assert uow.commits == 1
    assert document.id is not None


async def test_ingest_empty_content_raises():
    usecase = IngestDocument(documents=FakeDocRepo(), embedder=FakeEmbedder(), uow=FakeUoW())
    with pytest.raises(EmptyDocumentError):
        await usecase.execute(
            title="x", source_type="runbook", service=None, tags=[], content="   \n  "
        )
