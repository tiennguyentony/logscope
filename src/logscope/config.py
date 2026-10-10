"""Defaults shared by the commands. Everything here can be overridden by a flag."""

# How many rows the "top" tables show (--top).
DEFAULT_TOP = 10

# Percentiles reported by `logscope latency` when --p is not given.
DEFAULT_PERCENTILES = (50, 95, 99)

# Percentile definition used everywhere (see docs/adr/002-percentiles.md).
# Reported in --json output so downstream dashboards know what they got.
PERCENTILE_METHOD = "nearest-rank"

# A request slower than this (in seconds, from $request_time) counts as slow.
SLOW_REQUEST_SECONDS = 1.0
