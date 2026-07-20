"""Pure text chunking for RAG ingestion (docs/product/rag.md section "Ingestion & indexing").

Line-based greedy splitter that keeps Markdown heading breadcrumbs in each chunk and carries a small
overlap between chunks. Sizes are in characters (a coarse stand-in for the ~800-1000 token / ~100
token overlap target — one token is roughly four characters); a token-aware splitter can replace this
later without changing the port. Pure function, no I/O.
"""

from __future__ import annotations

import re

# ~900 tokens/chunk, ~100 token overlap, at ~4 chars/token.
DEFAULT_CHUNK_SIZE = 3600
DEFAULT_OVERLAP = 400

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")


def chunk_markdown(
    text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_OVERLAP
) -> list[str]:
    """Split `text` into overlapping chunks, prefixing each with its heading breadcrumb.

    Each emitted chunk starts with `[H1 > H2 > ...]` when headings are in scope, so the retriever and
    the LLM see where the excerpt sits in the document.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    overlap = max(0, min(overlap, chunk_size - 1))

    chunks: list[str] = []
    heading_stack: list[tuple[int, str]] = []
    buf: list[str] = []
    buf_len = 0

    def breadcrumb() -> str:
        return " > ".join(title for _, title in heading_stack)

    def flush() -> None:
        body = "\n".join(buf).strip()
        if not body:
            return
        crumb = breadcrumb()
        chunks.append(f"[{crumb}]\n{body}" if crumb else body)

    for line in text.splitlines():
        m = _HEADING.match(line)
        if m:
            level = len(m.group(1))
            heading_stack = [(lvl, t) for lvl, t in heading_stack if lvl < level]
            heading_stack.append((level, m.group(2).strip()))

        buf.append(line)
        buf_len += len(line) + 1

        if buf_len >= chunk_size:
            flush()
            # Carry the tail (up to `overlap` chars) into the next chunk for continuity.
            tail: list[str] = []
            tail_len = 0
            for prev in reversed(buf):
                if tail_len + len(prev) + 1 > overlap:
                    break
                tail.insert(0, prev)
                tail_len += len(prev) + 1
            buf = tail
            buf_len = tail_len

    flush()
    return chunks
