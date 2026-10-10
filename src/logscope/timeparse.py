"""Parse the --since / --until values people type on the command line."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

RELATIVE_RE = re.compile(r"^(?P<amount>\d+)(?P<unit>[smhd])$")
UNITS = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}


def parse_when(value: str, now: datetime) -> datetime:
    """Turn a --since/--until value into a timezone-aware datetime.

    Accepted forms:
      - relative to now: '90s', '15m', '2h', '7d'
      - ISO 8601 with an offset: '2025-11-02T06:00:00Z', '2025-11-02T01:00-04:00'
      - ISO 8601 without an offset: '2025-11-02 06:00', taken as UTC

    `now` must be timezone-aware; it comes from the injected clock.
    """
    value = value.strip()
    rel = RELATIVE_RE.match(value)
    if rel:
        delta = timedelta(**{UNITS[rel["unit"]]: int(rel["amount"])})
        return now - delta

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise ValueError(
            f"can't read {value!r} as a time; use e.g. 2h, 30m, "
            "or 2025-11-02T06:00:00Z"
        ) from None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed
