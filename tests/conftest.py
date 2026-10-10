from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest

from logscope.cli import Env, main

# Sunday 2 November 2025, 12:00 UTC.
NOW = datetime(2025, 11, 2, 12, 0, tzinfo=timezone.utc)

UA = "Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0"


def log_line(
    ip: str = "192.0.2.1",
    time: str = "02/Nov/2025:10:00:00 +0000",
    request: str = "GET / HTTP/1.1",
    status: int = 200,
    size: int | str = 512,
    referer: str = "-",
    agent: str = UA,
    request_time: float | None = 0.05,
    user: str = "-",
) -> str:
    line = f'{ip} - {user} [{time}] "{request}" {status} {size} "{referer}" "{agent}"'
    if request_time is not None:
        line += f" {request_time:.3f}"
    return line


@dataclass
class Result:
    code: int
    out: str
    err: str


@pytest.fixture
def write_log(tmp_path: Path):
    """Write lines to a log file in tmp_path and return its path."""

    def write(lines: list[str], name: str = "access.log") -> str:
        path = tmp_path / name
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return str(path)

    return write


@pytest.fixture
def cli():
    """Run the CLI in-process with a fixed clock and captured output."""

    def run(*argv: str) -> Result:
        out, err = io.StringIO(), io.StringIO()
        env = Env(stdout=out, stderr=err, clock=lambda: NOW)
        code = main(list(argv), env)
        return Result(code, out.getvalue(), err.getvalue())

    return run
