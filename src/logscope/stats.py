"""`logscope summary`: counts, error rate and the busiest paths and clients."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime

from logscope import config
from logscope.records import LogRecord


def is_error(status: int) -> bool:
    """Anything that isn't a successful response."""
    return status >= 300


def top_n(counts: Counter[str], n: int) -> list[tuple[str, int]]:
    """The n keys with the highest counts, highest first."""
    by_count: dict[int, set[str]] = defaultdict(set)
    for key, count in counts.items():
        by_count[count].add(key)

    result: list[tuple[str, int]] = []
    for count in sorted(by_count, reverse=True):
        for key in by_count[count]:
            if len(result) == n:
                return result
            result.append((key, count))
    return result


@dataclass
class Summary:
    requests: int
    errors: int
    error_rate: float
    unique_ips: int
    bytes_sent: int
    slow_requests: int
    first_seen: datetime | None
    last_seen: datetime | None
    status_classes: dict[str, int] = field(default_factory=dict)
    statuses: dict[int, int] = field(default_factory=dict)
    top_paths: list[tuple[str, int]] = field(default_factory=list)
    top_ips: list[tuple[str, int]] = field(default_factory=list)


def summarize(
    records: Iterable[LogRecord],
    top: int = config.DEFAULT_TOP,
    slow_seconds: float = config.SLOW_REQUEST_SECONDS,
) -> Summary:
    """One pass over the records; nothing is kept per record."""
    requests = errors = bytes_sent = slow = 0
    first: datetime | None = None
    last: datetime | None = None
    statuses: Counter[int] = Counter()
    paths: Counter[str] = Counter()
    ips: Counter[str] = Counter()

    for r in records:
        requests += 1
        bytes_sent += r.bytes_sent
        statuses[r.status] += 1
        paths[r.path] += 1
        ips[r.ip] += 1
        if is_error(r.status):
            errors += 1
        if r.request_time is not None and r.request_time > slow_seconds:
            slow += 1
        # Lines are usually in order, but merged or rotated logs may not be.
        if first is None or r.time < first:
            first = r.time
        if last is None or r.time > last:
            last = r.time

    classes: Counter[str] = Counter()
    for status, count in statuses.items():
        classes[f"{status // 100}xx"] += count

    return Summary(
        requests=requests,
        errors=errors,
        error_rate=errors / requests,
        unique_ips=len(ips),
        bytes_sent=bytes_sent,
        slow_requests=slow,
        first_seen=first,
        last_seen=last,
        status_classes=dict(sorted(classes.items())),
        statuses=dict(sorted(statuses.items())),
        top_paths=top_n(paths, top),
        top_ips=top_n(ips, top),
    )
