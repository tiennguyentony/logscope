"""Parse nginx access-log lines.

We read the nginx "combined" format, optionally followed by $request_time:

    log_format timed '$remote_addr - $remote_user [$time_local] '
                     '"$request" $status $body_bytes_sent '
                     '"$http_referer" "$http_user_agent" $request_time';

Plain "combined" lines (no $request_time) are accepted too; their
`request_time` is None. See docs/adr/001-log-format-and-stack.md.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from logscope.records import LogRecord

LINE_RE = re.compile(
    r"^(?P<ip>\d{1,3}(?:\.\d{1,3}){3}) "
    r"- (?P<user>\S+) "
    r"\[(?P<time>[^\]]+)\] "
    r'"(?P<request>[^"]*)" '
    r"(?P<status>\d{3}) "
    r"(?P<bytes>\d+|-) "
    r'"(?P<referer>[^"]*)" '
    r'"(?P<agent>[^"]*)"'
    r"(?: (?P<request_time>\d+(?:\.\d+)?))?$"
)

TIME_RE = re.compile(
    r"^(?P<day>\d{2})/(?P<month>[A-Za-z]{3})/(?P<year>\d{4})"
    r":(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2}) "
    r"(?P<sign>[+-])(?P<off_h>\d{2})(?P<off_m>\d{2})$"
)

# nginx always writes English month names, whatever the machine's locale is,
# so we don't use strptime's locale-dependent %b.
MONTHS = {
    name: number
    for number, name in enumerate(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
         "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        start=1,
    )
}


def parse_time(value: str) -> datetime:
    """Parse nginx's $time_local, e.g. '02/Nov/2025:01:30:00 -0400'."""
    m = TIME_RE.match(value)
    if not m or m["month"] not in MONTHS:
        raise ValueError(f"not an nginx timestamp: {value!r}")
    offset = timedelta(hours=int(m["off_h"]), minutes=int(m["off_m"]))
    if m["sign"] == "-":
        offset = -offset
    return datetime(
        int(m["year"]), MONTHS[m["month"]], int(m["day"]),
        int(m["hour"]), int(m["minute"]), int(m["second"]),
        tzinfo=timezone(offset),
    )


def split_request(request: str) -> tuple[str, str, str]:
    """Split '"GET /path?x=1 HTTP/1.1"' into method, target and protocol.

    Junk requests (TLS handshakes sent to port 80, empty requests) don't have
    three parts; they get method '-' and the whole request as the target.
    """
    parts = request.split(" ")
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    return "-", request, "-"


def strip_query(target: str) -> str:
    """'/search?q=shoes' -> '/search'. Paths are grouped without their query."""
    return target.split("?", 1)[0]


def _dash_to_none(value: str) -> str | None:
    return None if value == "-" else value


def parse_line(line: str) -> LogRecord | None:
    """Parse one line. Returns None if the line isn't a valid access-log line."""
    line = line.rstrip("\r\n")
    m = LINE_RE.match(line)
    if not m:
        return None
    try:
        time = parse_time(m["time"])
    except ValueError:
        return None

    method, target, protocol = split_request(m["request"])
    request_time = m["request_time"]
    return LogRecord(
        ip=m["ip"],
        user=_dash_to_none(m["user"]),
        time=time,
        method=method,
        target=target,
        path=strip_query(target),
        protocol=protocol,
        status=int(m["status"]),
        bytes_sent=0 if m["bytes"] == "-" else int(m["bytes"]),
        referer=_dash_to_none(m["referer"]),
        user_agent=m["agent"],
        request_time=float(request_time) if request_time is not None else None,
        raw=line,
    )
