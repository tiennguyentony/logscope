"""Render results as plain-text tables or JSON.

Results go to stdout; warnings and errors go to stderr (see cli.py), so
`logscope summary access.log --json | jq .` always gets clean JSON.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import Any, TextIO

from logscope import config
from logscope.latency import LatencyReport, LatencyStats
from logscope.records import LogRecord
from logscope.stats import Summary


def table(headers: Sequence[str], rows: Iterable[Sequence[Any]], right: Sequence[int] = ()) -> str:
    """A plain-text table. Columns whose index is in `right` are right-aligned."""
    cells = [[str(h) for h in headers]] + [[str(c) for c in row] for row in rows]
    widths = [max(len(row[i]) for row in cells) for i in range(len(headers))]

    def fmt(row: list[str]) -> str:
        parts = [
            cell.rjust(widths[i]) if i in right else cell.ljust(widths[i])
            for i, cell in enumerate(row)
        ]
        return "  ".join(parts).rstrip()

    lines = [fmt(cells[0]), "  ".join("-" * w for w in widths)]
    lines += [fmt(row) for row in cells[1:]]
    return "\n".join(lines)


def percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def millis(seconds: float) -> str:
    return f"{seconds * 1000:,.0f} ms"


def p_label(p: float) -> str:
    return f"p{p:g}"


def iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


# --- summary ---------------------------------------------------------------

def summary_text(s: Summary) -> str:
    overview = table(
        ["", ""],
        [
            ["Requests", f"{s.requests:,}"],
            ["Errors", f"{s.errors:,} ({percent(s.error_rate)})"],
            ["Unique IPs", f"{s.unique_ips:,}"],
            ["Bytes sent", f"{s.bytes_sent:,}"],
            [f"Slow (> {config.SLOW_REQUEST_SECONDS:g}s)", f"{s.slow_requests:,}"],
            ["First request", iso(s.first_seen) or "-"],
            ["Last request", iso(s.last_seen) or "-"],
        ],
    ).split("\n", 2)[2]  # drop the empty header row

    classes = table(["Class", "Requests"], s.status_classes.items(), right=[1])
    statuses = table(["Status", "Requests"], s.statuses.items(), right=[1])
    paths = table(["Path", "Requests"], s.top_paths, right=[1])
    ips = table(["IP", "Requests"], s.top_ips, right=[1])
    return "\n\n".join([overview, classes, statuses, paths, ips])


def summary_json(s: Summary) -> dict[str, Any]:
    return {
        "requests": s.requests,
        "errors": s.errors,
        "error_rate": round(s.error_rate, 4),
        "unique_ips": s.unique_ips,
        "bytes_sent": s.bytes_sent,
        "slow_requests": s.slow_requests,
        "first_seen": iso(s.first_seen),
        "last_seen": iso(s.last_seen),
        "status_classes": s.status_classes,
        "statuses": {str(k): v for k, v in s.statuses.items()},
        "top_paths": [{"path": p, "requests": n} for p, n in s.top_paths],
        "top_ips": [{"ip": ip, "requests": n} for ip, n in s.top_ips],
    }


# --- latency ---------------------------------------------------------------

def _latency_row(label: str, st: LatencyStats, ps: Sequence[float]) -> list[str]:
    return [label, f"{st.count:,}", millis(st.mean)] + [
        millis(st.percentiles[p]) for p in ps
    ] + [millis(st.max), f"{st.slow:,}"]


def latency_text(report: LatencyReport, ps: Sequence[float]) -> str:
    if report.overall is None:
        return f"No timed requests ({report.requests:,} requests, none with $request_time)."
    headers = ["", "Count", "Mean"] + [p_label(p) for p in ps] + ["Max", "Slow"]
    right = list(range(1, len(headers)))
    rows = [_latency_row("All requests", report.overall, ps)]
    rows += [_latency_row(path, st, ps) for path, st in report.by_path]
    text = table(headers, rows, right=right)
    if report.untimed:
        text += f"\n\n{report.untimed:,} requests had no $request_time and are not included."
    return text


def _latency_stats_json(st: LatencyStats) -> dict[str, Any]:
    return {
        "count": st.count,
        "mean_ms": round(st.mean * 1000, 1),
        "max_ms": round(st.max * 1000, 1),
        "percentiles_ms": {p_label(p): round(v * 1000, 1) for p, v in st.percentiles.items()},
        "slow": st.slow,
    }


def latency_json(report: LatencyReport) -> dict[str, Any]:
    return {
        "method": config.PERCENTILE_METHOD,
        "requests": report.requests,
        "untimed": report.untimed,
        "overall": _latency_stats_json(report.overall) if report.overall else None,
        "by_path": [{"path": p, **_latency_stats_json(st)} for p, st in report.by_path],
    }


# --- filter ----------------------------------------------------------------

def record_json(r: LogRecord) -> dict[str, Any]:
    return {
        "ip": r.ip,
        "time": r.time.isoformat(),
        "method": r.method,
        "path": r.path,
        "target": r.target,
        "status": r.status,
        "bytes": r.bytes_sent,
        "referer": r.referer,
        "user_agent": r.user_agent,
        "request_time": r.request_time,
    }


def write_records(records: Iterable[LogRecord], out: TextIO, as_json: bool) -> int:
    """Write matching records (raw lines, or JSON Lines). Returns how many."""
    count = 0
    for r in records:
        out.write((json.dumps(record_json(r)) if as_json else r.raw) + "\n")
        count += 1
    return count


def write_json(data: dict[str, Any], out: TextIO) -> None:
    json.dump(data, out, indent=2)
    out.write("\n")
