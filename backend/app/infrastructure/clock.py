"""System clock adapter implementing the domain `Clock` port."""

from __future__ import annotations

from datetime import datetime, timezone


class SystemClock:
    """Returns the real, timezone-aware current time."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)
