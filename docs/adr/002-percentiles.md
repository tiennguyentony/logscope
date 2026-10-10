# ADR-002: Nearest-rank percentiles

**Status:** Accepted

## Context

There are many percentile definitions. numpy's default interpolates between
neighbouring values, so "p95 = 412 ms" may be a latency no request actually
had. Our alerting (the load balancer's) and our SLO reports use the
nearest-rank definition, and people compare logscope's numbers with them.

## Decision

- `logscope latency` uses the **nearest-rank** method: sort the n values;
  the p-th percentile is the value at rank `ceil(p / 100 * n)` (1-based).
  p100 is the maximum. p must be in (0, 100].
- Every reported percentile is a value that was actually observed.
- `--json` output includes `"method": "nearest-rank"` (from
  `config.PERCENTILE_METHOD`) so consumers know what they're getting.
- Requests without `$request_time` are left out of the calculation and
  counted separately as "untimed". Counting them as 0 ms would make every
  percentile look better than reality.

## Consequences

- Numbers match the load balancer's dashboards.
- For small samples, nearest-rank jumps in steps (p95 of 20 values is the
  19th value). That's expected.
- Results differ from `numpy.percentile` with default settings. Use
  `method="inverted_cdf"` in numpy to compare.
