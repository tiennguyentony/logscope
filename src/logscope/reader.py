"""Turn a log file into a stream of LogRecords."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import TextIO

from logscope.parser import parse_line
from logscope.records import LogRecord

Opener = Callable[[str], TextIO]


def open_log(path: str) -> TextIO:
    # Access logs are mostly ASCII, but user agents and paths can contain
    # anything a client sends. Never crash on a bad byte.
    return open(path, encoding="utf-8", errors="replace", newline="")


def read_records(path: str, opener: Opener = open_log) -> Iterator[LogRecord]:
    """Yield the records in `path`, in file order."""
    with opener(path) as f:
        lines = f.readlines()
    for line in lines:
        if not line.strip():
            continue
        record = parse_line(line)
        if record is not None:
            yield record
