"""In-process pub/sub for live incident-analysis progress (SSE streaming design, decision
2026-07-20). One `uvicorn` process only — no cross-restart durability, no multi-worker fan-out.

A background task calls `open()` when analysis starts and `publish()` for each stage/terminal
event; the SSE endpoint calls `subscribe()` to attach. `close()` only drops the bus's own
bookkeeping entry — it never touches a queue a subscriber already holds a reference to, so a
subscriber that attached before the terminal event was published still drains it even if the
producer closes right after publishing.
"""

from __future__ import annotations

import asyncio


class IncidentEventBus:
    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue] = {}

    def open(self, incident_id: str) -> asyncio.Queue:
        """Register a live producer for `incident_id`, creating its channel."""
        queue: asyncio.Queue = asyncio.Queue()
        self._queues[incident_id] = queue
        return queue

    def subscribe(self, incident_id: str) -> asyncio.Queue | None:
        """Attach to the live channel for `incident_id`, if a producer has opened one."""
        return self._queues.get(incident_id)

    async def publish(self, incident_id: str, event: dict) -> None:
        """Enqueue an event. No-op if nobody has opened a channel for this incident."""
        queue = self._queues.get(incident_id)
        if queue is not None:
            await queue.put(event)

    def close(self, incident_id: str) -> None:
        """Drop the channel's registration. Safe to call even if never opened."""
        self._queues.pop(incident_id, None)
