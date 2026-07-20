"""Unit tests for the ProgressReporter port's no-op default.

`NullReporter` is the default passed through IngestIncident/analyzers when no SSE subscriber is
involved (e.g. the existing tests and the dev/debug harness) so they need no changes to keep
working once analyzers start accepting a reporter.
"""

import pytest

from app.domain.incidents.ports import NullReporter

pytestmark = pytest.mark.asyncio


async def test_null_reporter_stage_without_detail_does_nothing():
    reporter = NullReporter()
    assert await reporter.stage("triage") is None


async def test_null_reporter_stage_with_detail_does_nothing():
    reporter = NullReporter()
    assert await reporter.stage("retrieve", "6 evidence chunks") is None
