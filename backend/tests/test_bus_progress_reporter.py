"""Unit tests for BusProgressReporter — the ProgressReporter adapter that publishes analyzer
stages onto an IncidentEventBus channel as SSE-ready event dicts.
"""

import pytest

from app.infrastructure.events import BusProgressReporter, IncidentEventBus

pytestmark = pytest.mark.asyncio


async def test_stage_publishes_a_stage_event_with_a_known_label():
    bus = IncidentEventBus()
    bus.open("inc-1")
    queue = bus.subscribe("inc-1")
    reporter = BusProgressReporter(bus, "inc-1")

    await reporter.stage("triage")

    event = await queue.get()
    assert event == {
        "event": "stage",
        "data": {"stage": "triage", "label": "Triaging incident", "detail": None},
    }


async def test_stage_includes_detail_when_given():
    bus = IncidentEventBus()
    bus.open("inc-1")
    queue = bus.subscribe("inc-1")
    reporter = BusProgressReporter(bus, "inc-1")

    await reporter.stage("retrieve", "6 evidence chunks")

    event = await queue.get()
    assert event["data"]["detail"] == "6 evidence chunks"


async def test_stage_falls_back_to_a_humanized_label_for_unknown_stage_names():
    bus = IncidentEventBus()
    bus.open("inc-1")
    queue = bus.subscribe("inc-1")
    reporter = BusProgressReporter(bus, "inc-1")

    await reporter.stage("some_new_step")

    event = await queue.get()
    assert event["data"]["label"] == "Some new step"


async def test_stage_is_a_noop_when_nobody_opened_the_incident():
    bus = IncidentEventBus()
    reporter = BusProgressReporter(bus, "never-opened")
    await reporter.stage("triage")  # must not raise
