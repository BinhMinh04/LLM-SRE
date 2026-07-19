"""configurable embedding dimension (decision 0016)

Revision ID: 0002_embedding_dim
Revises: 0001_initial
Create Date: 2026-07-19

Resizes `doc_chunks.embedding` to `settings.embedding_dim` when it differs from the 1024 baseline
(e.g. Jina jina-embeddings-v3 = 768). pgvector cannot cast between dimensions, and one database serves
one embedding provider at a time, so the column is dropped and re-added at the target dimension and
the HNSW index is rebuilt — any existing chunks must be re-embedded with the new provider.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

from app.infrastructure.config import get_settings

revision: str = "0002_embedding_dim"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_BASELINE_DIM = 1024


def _resize(dim: int) -> None:
    op.drop_index("ix_doc_chunks_embedding_hnsw", table_name="doc_chunks")
    op.drop_column("doc_chunks", "embedding")
    op.add_column("doc_chunks", sa.Column("embedding", Vector(dim), nullable=False))
    op.execute(
        "CREATE INDEX ix_doc_chunks_embedding_hnsw "
        "ON doc_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def upgrade() -> None:
    dim = get_settings().embedding_dim
    if dim != _BASELINE_DIM:
        _resize(dim)


def downgrade() -> None:
    _resize(_BASELINE_DIM)
