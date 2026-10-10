# ADR-003: Timestamps are instants, compared in UTC

**Status:** Accepted

## Context

nginx writes `$time_local` with the server's UTC offset, e.g.
`02/Nov/2025:01:30:00 -0500`. Our servers run in different time zones, and
the offset changes when daylight saving starts or ends: on the night it
ends, 01:00-02:00 local happens twice, once at -0400 and once at -0500.
Incident timelines are written in UTC.

## Decision

- The parser keeps every timestamp as a timezone-aware `datetime` with the
  offset from the log. It never converts to the machine's local time.
- `--since` and `--until` are parsed into aware datetimes: relative values
  (`2h`) from the injected clock, ISO 8601 values with their offset, and ISO
  values without an offset as UTC.
- Comparisons are between instants (aware datetimes), never between
  wall-clock times. `01:30 -0400` is before `01:00 -0500`.
- Nothing calls `datetime.now()` except `utc_now()` in `cli.py`. Everything
  else receives the clock through `Env`, so tests can fix "now".

## Consequences

- `--since 2025-11-02T06:00:00Z` means the same thing on every machine and
  for every server's log.
- Output shows timestamps with the offset they were logged with, so they
  match what people see in the raw file.
- Logs from several servers can be merged or sorted by `record.time`
  directly, whatever offsets they were written with.
