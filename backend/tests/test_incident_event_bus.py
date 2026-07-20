"""Unit tests for IncidentEventBus — the in-process pub/sub channel backing SSE streaming.

No DB, no network: pure asyncio.Queue bookkeeping. Covers the producer/subscriber lifecycle and
the race-avoidance property the streaming design relies on (docs/.claude/specs/2026-07-20-...):
a subscriber that already holds a queue reference keeps draining it even after the bus "closes"
that incident's registration.
"""

import pytest

from app.infrastructure.events import IncidentEventBus

pytestmark = pytest.mark.asyncio


def test_subscribe_without_open_returns_none():
    bus = IncidentEventBus()
    assert bus.subscribe("missing-incident") is None


async def test_open_then_subscribe_returns_the_same_queue():
    bus = IncidentEventBus()
    opened = bus.open("inc-1")
    subscribed = bus.subscribe("inc-1")
    assert subscribed is opened


async def test_publish_enqueues_event_for_subscriber():
    bus = IncidentEventBus()
    bus.open("inc-1")
    queue = bus.subscribe("inc-1")
    await bus.publish("inc-1", {"event": "stage", "data": {"stage": "triage"}})
    event = await queue.get()
    assert event == {"event": "stage", "data": {"stage": "triage"}}


async def test_publish_without_open_is_a_noop():
    bus = IncidentEventBus()
    # Must not raise even though nobody opened/subscribed this incident.
    await bus.publish("never-opened", {"event": "stage", "data": {}})


async def test_close_removes_registration_so_new_subscribers_get_none():
    bus = IncidentEventBus()
    bus.open("inc-1")
    bus.close("inc-1")
    assert bus.subscribe("inc-1") is None


async def test_close_is_idempotent_when_never_opened():
    bus = IncidentEventBus()
    bus.close("never-opened")  # must not raise


async def test_subscriber_still_drains_events_enqueued_before_close():
    """The race-avoidance property: close() only removes the bus's own bookkeeping entry — it
    must not clear a queue a subscriber already holds a reference to, so a subscriber that
    attached before the terminal event was published still receives that event.
    """
    bus = IncidentEventBus()
    bus.open("inc-1")
    queue = bus.subscribe("inc-1")  # subscriber attaches first, holds a direct reference
    await bus.publish("inc-1", {"event": "analyzed", "data": {"severity": "critical"}})
    bus.close("inc-1")  # producer finishes and closes right after publishing
    event = await queue.get()  # subscriber still reads the terminal event it already had
    assert event == {"event": "analyzed", "data": {"severity": "critical"}}
