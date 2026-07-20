"""Test-only helper for reading Server-Sent Events from an httpx streaming response."""

import json


async def iter_sse(response):
    """Yield (event, data) tuples as they arrive from an SSE response body."""
    event_name, data_lines = None, []
    async for line in response.aiter_lines():
        if line.startswith("event:"):
            event_name = line[len("event:") :].strip()
        elif line.startswith("data:"):
            data_lines.append(line[len("data:") :].strip())
        elif line == "":
            if event_name is not None:
                data = json.loads("".join(data_lines)) if data_lines else None
                yield event_name, data
            event_name, data_lines = None, []
