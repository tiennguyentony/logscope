from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class LogRecord:
    """One parsed access-log line.

    `time` is timezone-aware and keeps the offset the server wrote, so
    `time.utcoffset()` tells you which offset the line was logged with.
    `path` has the query string removed; `target` is the request target
    exactly as it appeared in the log.
    """

    ip: str
    user: str | None
    time: datetime
    method: str
    target: str
    path: str
    protocol: str
    status: int
    bytes_sent: int
    referer: str | None
    user_agent: str
    request_time: float | None
    raw: str

    @property
    def status_class(self) -> str:
        return f"{self.status // 100}xx"
