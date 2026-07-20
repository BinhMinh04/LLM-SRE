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

_STAGE_LABELS = {
    "triage": "Triaging incident",
    "retrieve": "Retrieving evidence",
    "diagnose": "Diagnosing root cause",
    "critic": "Critiquing hypothesis",
    "synthesize": "Synthesizing analysis",
    "analyze": "Analyzing incident",
    "cached": "Using cached analysis",
}


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


class BusProgressReporter:
    """`ProgressReporter` adapter that publishes each stage as an SSE-ready event dict."""

    def __init__(self, bus: IncidentEventBus, incident_id: str) -> None:
        self._bus = bus
        self._incident_id = incident_id

    async def stage(self, name: str, detail: str | None = None) -> None:
        label = _STAGE_LABELS.get(name, name.replace("_", " ").capitalize())
        await self._bus.publish(
            self._incident_id,
            {"event": "stage", "data": {"stage": name, "label": label, "detail": detail}},
        )
