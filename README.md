# Logscope

Quick answers from web-server access logs, straight from the terminal.

When something looks off in production, the first questions are always the
same: how many requests, how many errors, which endpoints, who's hammering
us, how slow is it? Logscope answers them from the raw access log in a
second, without shipping anything to a logging platform first.

## Features

- `logscope summary`: request count, error rate, status breakdown, top paths
  and top client IPs
- `logscope latency`: response-time percentiles (p50/p95/p99 or any you
  ask for), overall and per path
- `logscope filter`: print just the lines you care about, by time window,
  status and path
- Plain-text tables for humans, `--json` for scripts and dashboards
- Reads nginx (combined), Apache (common and combined) and JSON-lines logs;
  the format is detected automatically
- Export to Elasticsearch: `logscope export access.log --es http://localhost:9200`

## Tech stack

- Python 3.11+
- [Click](https://click.palletsprojects.com) for the command-line interface
- pytest for tests

## Installation

```bash
pip install logscope
logscope --help
```

For development:

```bash
git clone https://github.com/tiennguyentony/logscope.git
cd logscope
uv sync
uv run pytest
uv run logscope summary samples/access.log
```

## Usage

```bash
logscope summary samples/access.log
logscope summary samples/access.log --top 5 --json

logscope latency samples/access.log                    # p50, p95, p99
logscope latency samples/access.log --p 50,90,99.9 --by-path 10

logscope filter samples/access.log --status 5xx
logscope filter samples/access.log --since 2025-11-02T07:30:00Z --until 2025-11-02T08:00:00Z
logscope filter samples/access.log --path '/api/**' --json
```

Options shared by every command:

| Option | Example | Meaning |
|---|---|---|
| `--since` | `2h`, `30m`, `2025-11-02T06:00:00Z` | requests at or after this time |
| `--until` | `2025-11-02T08:00:00-05:00` | requests before this time |
| `--status` | `404`, `5xx`, `4xx,500` | only these statuses |
| `--path` | `/products/*`, `/static/**/*.js` | only paths matching the glob |
| `--json` | | JSON instead of a table (`filter` prints JSON Lines) |

Times without an offset are taken as UTC. In path globs `*` stays within one
path segment and `**` spans segments.

What the numbers mean:

- **Error rate** is the share of 4xx and 5xx responses.
- **Paths** are grouped without their query string: `/search?q=boots` and
  `/search?q=socks` both count as `/search`.
- **Latency** comes from `$request_time` at the end of each line. Lines
  without it are reported as "untimed" and left out of the percentiles.
- Results go to stdout, messages to stderr, so `--json | jq` always works.

## Sample data

`samples/access.log` is one night (about 3,300 requests) of a small web
shop's nginx log, including a short outage of the orders API.
`samples/edge-cases.log` has a handful of unusual lines. Both are generated
by `samples/generate_samples.py`; re-run it after changing it.

## Project layout

```
src/logscope/
  cli.py          argument parsing and composition root (main, Env)
  parser.py       one log line -> LogRecord
  reader.py       file -> stream of LogRecords
  filters.py      --since/--until/--status/--path
  timeparse.py    parsing --since/--until values
  stats.py        summary
  latency.py      latency report
  percentiles.py  percentile maths
  output.py       tables and JSON
  legacy/         Elasticsearch exporter
samples/          sample logs and their generator
docs/adr/         architecture decision records
tests/            pytest suite
```

## Docs

Design decisions are recorded in [`docs/adr`](docs/adr).
