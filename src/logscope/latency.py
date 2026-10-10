"""`logscope latency`: response-time percentiles from $request_time."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from logscope import config
from logscope.percentiles import percentile
from logscope.records import LogRecord


@dataclass
class LatencyStats:
    count: int
    mean: float
    max: float
    percentiles: dict[float, float]
    slow: int


@dataclass
class LatencyReport:
    requests: int
    untimed: int
    overall: LatencyStats | None
    by_path: list[tuple[str, LatencyStats]]


def latency_stats(
    times: list[float],
    ps: Sequence[float],
    slow_seconds: float = config.SLOW_REQUEST_SECONDS,
) -> LatencyStats:
    times = sorted(times)
    return LatencyStats(
        count=len(times),
        mean=sum(times) / len(times),
        max=times[-1],
        percentiles={p: percentile(times, p) for p in ps},
        slow=sum(1 for t in times if t > slow_seconds),
    )


def latency_report(
    records: Iterable[LogRecord],
    ps: Sequence[float] = config.DEFAULT_PERCENTILES,
    by_path: int = 0,
    slow_seconds: float = config.SLOW_REQUEST_SECONDS,
) -> LatencyReport:
    """Percentiles over every timed request, optionally per path.

    Lines without $request_time are counted in `untimed` and left out of the
    numbers. Treating them as 0 ms would drag every percentile down.
    """
    requests = untimed = 0
    times: list[float] = []
    per_path: dict[str, list[float]] = defaultdict(list)

    for r in records:
        requests += 1
        if r.request_time is None:
            untimed += 1
            continue
        times.append(r.request_time)
        if by_path:
            per_path[r.path].append(r.request_time)

    overall = latency_stats(times, ps, slow_seconds) if times else None

    paths: list[tuple[str, LatencyStats]] = []
    if by_path:
        busiest = sorted(per_path.items(), key=lambda kv: (-len(kv[1]), kv[0]))
        paths = [(path, latency_stats(ts, ps, slow_seconds)) for path, ts in busiest[:by_path]]

    return LatencyReport(requests=requests, untimed=untimed, overall=overall, by_path=paths)
