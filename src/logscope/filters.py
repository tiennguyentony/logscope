"""Decide which records a command looks at (--since, --until, --status, --path)."""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime

from logscope.records import LogRecord

STATUS_TOKEN_RE = re.compile(r"^[1-5](?:\d\d|xx)$")


@dataclass(frozen=True)
class StatusMatcher:
    """Matches statuses like '404', '5xx' or a mix: '4xx,500'."""

    exact: frozenset[int]
    classes: frozenset[int]

    @classmethod
    def parse(cls, spec: str) -> StatusMatcher:
        exact: set[int] = set()
        classes: set[int] = set()
        for token in spec.lower().split(","):
            token = token.strip()
            if not STATUS_TOKEN_RE.match(token):
                raise ValueError(f"bad status {token!r}; use e.g. 404, 5xx or 4xx,500")
            if token.endswith("xx"):
                classes.add(int(token[0]))
            else:
                exact.add(int(token))
        return cls(frozenset(exact), frozenset(classes))

    def __call__(self, status: int) -> bool:
        return status in self.exact or status // 100 in self.classes


def glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Compile a path glob into a regex that must match the whole path.

      *     any characters except '/'
      ?     one character except '/'
      **/   zero or more whole directories
      **    (at the end) anything, including '/'

    Example: '/static/**/*.js' matches '/static/app.js' and
    '/static/js/vendor/react.js', but not '/static/app.json'.
    """
    out: list[str] = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(.*/)*")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out))


@dataclass(frozen=True)
class RecordFilter:
    since: datetime | None = None
    until: datetime | None = None
    status: StatusMatcher | None = None
    path: re.Pattern[str] | None = None

    def matches(self, record: LogRecord) -> bool:
        # Compare as wall-clock time, so --since lines up with the timestamps
        # people see when they open the log file.
        when = record.time.replace(tzinfo=None)
        if self.since is not None and when < self.since.replace(tzinfo=None):
            return False
        if self.until is not None and when >= self.until.replace(tzinfo=None):
            return False
        if self.status is not None and not self.status(record.status):
            return False
        if self.path is not None and not self.path.fullmatch(record.path):
            return False
        return True

    def apply(self, records: Iterable[LogRecord]) -> Iterator[LogRecord]:
        return (r for r in records if self.matches(r))
