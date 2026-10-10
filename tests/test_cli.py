import json

from .conftest import log_line

LINES = [
    log_line(ip="192.0.2.1", time="02/Nov/2025:10:00:00 +0000", request="GET / HTTP/1.1", status=200, request_time=0.020),
    log_line(ip="192.0.2.1", time="02/Nov/2025:10:01:00 +0000", request="GET /products/7 HTTP/1.1", status=200, request_time=0.080),
    log_line(ip="192.0.2.2", time="02/Nov/2025:10:02:00 +0000", request="POST /api/v1/orders HTTP/1.1", status=201, request_time=0.300),
    log_line(ip="192.0.2.2", time="02/Nov/2025:10:03:00 +0000", request="POST /api/v1/orders HTTP/1.1", status=502, request_time=12.0),
    log_line(ip="192.0.2.1", time="02/Nov/2025:11:30:00 +0000", request="GET /missing HTTP/1.1", status=404, request_time=0.010),
]


def test_summary_table(cli, write_log):
    result = cli("summary", write_log(LINES))

    assert result.code == 0
    assert "Requests       5" in result.out
    assert "Errors         2 (40.0%)" in result.out
    assert "/api/v1/orders" in result.out
    assert result.err == ""


def test_summary_json(cli, write_log):
    result = cli("summary", write_log(LINES), "--json", "--top", "1")

    data = json.loads(result.out)
    assert data["requests"] == 5
    assert data["error_rate"] == 0.4
    assert data["statuses"] == {"200": 2, "201": 1, "404": 1, "502": 1}
    assert data["top_ips"] == [{"ip": "192.0.2.1", "requests": 3}]
    assert data["first_seen"] == "2025-11-02T10:00:00+00:00"


def test_summary_with_status_filter(cli, write_log):
    data = json.loads(cli("summary", write_log(LINES), "--status", "2xx", "--json").out)
    assert data["requests"] == 3


def test_latency_table(cli, write_log):
    result = cli("latency", write_log(LINES), "--p", "50,99")

    assert result.code == 0
    assert "p50" in result.out and "p99" in result.out
    assert "12,000 ms" in result.out


def test_latency_json_reports_the_method(cli, write_log):
    data = json.loads(cli("latency", write_log(LINES), "--p", "50", "--json").out)
    assert data["method"] == "nearest-rank"
    assert data["overall"]["count"] == 5
    assert data["overall"]["percentiles_ms"] == {"p50": 80.0}


def test_latency_rejects_bad_percentiles(cli, write_log):
    result = cli("latency", write_log(LINES), "--p", "0,50")
    assert result.code == 2
    assert "out of range" in result.err


def test_filter_prints_raw_lines(cli, write_log):
    result = cli("filter", write_log(LINES), "--status", "5xx")

    assert result.out.splitlines() == [LINES[3]]
    assert result.err == "1 matching requests\n"


def test_filter_json_lines(cli, write_log):
    result = cli("filter", write_log(LINES), "--path", "/api/**", "--json")

    rows = [json.loads(line) for line in result.out.splitlines()]
    assert [r["status"] for r in rows] == [201, 502]
    assert rows[0]["request_time"] == 0.3


def test_filter_relative_since_uses_the_injected_clock(cli, write_log):
    # NOW is 12:00 UTC, so "1h" means 11:00 onwards.
    result = cli("filter", write_log(LINES), "--since", "1h")
    assert result.out.splitlines() == [LINES[4]]


def test_filter_time_window(cli, write_log):
    result = cli("filter", write_log(LINES), "--since", "2025-11-02T10:01:00Z", "--until", "2025-11-02T10:03:00Z")
    assert result.out.splitlines() == LINES[1:3]


def test_blank_lines_are_ignored(cli, write_log):
    data = json.loads(cli("summary", write_log(LINES[:2] + ["", ""]), "--json").out)
    assert data["requests"] == 2


def test_missing_file(cli, tmp_path):
    result = cli("summary", str(tmp_path / "nope.log"))
    assert result.code == 1
    assert "can't read" in result.err


def test_bad_since(cli, write_log):
    result = cli("filter", write_log(LINES), "--since", "yesterday-ish")
    assert result.code == 2
    assert result.err.startswith("logscope: can't read 'yesterday-ish'")
