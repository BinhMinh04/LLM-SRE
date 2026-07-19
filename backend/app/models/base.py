"""Declarative base + shared column helpers.

SQLAlchemy 2.0 typed ORM: https://docs.sqlalchemy.org/en/20/orm/declarative_styles.html
"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def utcnow_column() -> Mapped[datetime]:
    """A timezone-aware timestamp defaulting to now() at the database."""
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
