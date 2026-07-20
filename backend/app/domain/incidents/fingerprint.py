"""Incident fingerprint — the cache key, relocated into the domain (decision 0015).

Preserved verbatim from the Step 0 brain: `service | normalized-error-signature | deploy-version`.
The signature strips digits and hex ids so repeats of the same error collapse to one key, and a
different deploy version yields a different fingerprint — forcing re-analysis so a stale cache cannot
misdiagnose a post-deploy incident. Pure function; no I/O.
"""

from __future__ import annotations

import hashlib
import re


def fingerprint(ctx: dict) -> str:
    """Cache key: service + error signature + current change version."""
    if ctx.get("sample_logs"):
        raw = ctx["sample_logs"][0].get("message", "")
    else:
        raw = ctx.get("alert", "")
    error_sig = re.sub(r"[0-9a-f]{8,}|\d+", "", raw).strip()
    version = (ctx.get("recent_deploy") or {}).get("version", "")
    key = f"{ctx.get('service')}|{error_sig}|{version}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]
