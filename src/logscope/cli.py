"""Command-line entry point and composition root.

`main(argv, env)` is the only place that touches the outside world: the
clock, stdout/stderr and opening files all come in through `Env`. Tests pass
a fixed clock, StringIO streams and their own opener.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TextIO

from logscope import __version__, config, output
from logscope.filters import RecordFilter, StatusMatcher, glob_to_regex
from logscope.latency import latency_report
from logscope.percentiles import parse_percentiles
from logscope.reader import Opener, open_log, read_records
from logscope.records import LogRecord
from logscope.stats import summarize
from logscope.timeparse import parse_when


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Env:
    stdout: TextIO = field(default_factory=lambda: sys.stdout)
    stderr: TextIO = field(default_factory=lambda: sys.stderr)
    clock: Callable[[], datetime] = utc_now
    opener: Opener = open_log


class UsageError(Exception):
    """Bad input from the user; reported as one line on stderr, exit code 2."""


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("file", help="nginx access log")
    common.add_argument("--since", help="only requests at or after this time (2h, 30m, ISO 8601)")
    common.add_argument("--until", help="only requests before this time (2h, 30m, ISO 8601)")
    common.add_argument("--status", help="only these statuses, e.g. 404, 5xx, 4xx,500")
    common.add_argument("--path", help="only paths matching this glob, e.g. '/api/**'")
    common.add_argument("--json", action="store_true", help="print JSON instead of a table")

    parser = argparse.ArgumentParser(
        prog="logscope",
        description="Quick answers from nginx access logs.",
    )
    parser.add_argument("--version", action="version", version=f"logscope {__version__}")
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    summary = sub.add_parser("summary", parents=[common], help="requests, errors, top paths and IPs")
    summary.add_argument("--top", type=int, default=config.DEFAULT_TOP, help="rows in the top tables")

    latency = sub.add_parser("latency", parents=[common], help="response-time percentiles")
    latency.add_argument(
        "--p",
        default=",".join(str(p) for p in config.DEFAULT_PERCENTILES),
        help="comma-separated percentiles (default: %(default)s)",
    )
    latency.add_argument(
        "--by-path", type=int, default=0, metavar="N",
        help="also show the N busiest paths",
    )

    sub.add_parser("filter", parents=[common], help="print the matching lines")
    return parser


def build_filter(args: argparse.Namespace, now: datetime) -> RecordFilter:
    try:
        return RecordFilter(
            since=parse_when(args.since, now) if args.since else None,
            until=parse_when(args.until, now) if args.until else None,
            status=StatusMatcher.parse(args.status) if args.status else None,
            path=glob_to_regex(args.path) if args.path else None,
        )
    except ValueError as e:
        raise UsageError(str(e)) from None


def cmd_summary(args: argparse.Namespace, records: Iterator[LogRecord], env: Env) -> None:
    result = summarize(records, top=args.top)
    if args.json:
        output.write_json(output.summary_json(result), env.stdout)
    else:
        env.stdout.write(output.summary_text(result) + "\n")


def cmd_latency(args: argparse.Namespace, records: Iterator[LogRecord], env: Env) -> None:
    try:
        ps = parse_percentiles(args.p)
    except ValueError as e:
        raise UsageError(str(e)) from None
    report = latency_report(records, ps, by_path=args.by_path)
    if args.json:
        output.write_json(output.latency_json(report), env.stdout)
    else:
        env.stdout.write(output.latency_text(report, ps) + "\n")


def cmd_filter(args: argparse.Namespace, records: Iterator[LogRecord], env: Env) -> None:
    count = output.write_records(records, env.stdout, as_json=args.json)
    env.stderr.write(f"{count:,} matching requests\n")


COMMANDS = {"summary": cmd_summary, "latency": cmd_latency, "filter": cmd_filter}


def main(argv: Sequence[str] | None = None, env: Env | None = None) -> int:
    env = env or Env()
    args = build_parser().parse_args(argv)
    try:
        record_filter = build_filter(args, env.clock())
        records = record_filter.apply(read_records(args.file, env.opener))
        COMMANDS[args.command](args, records, env)
    except UsageError as e:
        env.stderr.write(f"logscope: {e}\n")
        return 2
    except OSError as e:
        env.stderr.write(f"logscope: can't read {args.file}: {e.strerror or e}\n")
        return 1
    return 0


def run() -> None:
    """Console-script entry point."""
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        # `logscope filter big.log | head` closes the pipe early; that's fine.
        sys.exit(0)
