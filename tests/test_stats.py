from collections import Counter

from logscope.parser import parse_line
from logscope.stats import summarize, top_n

from .conftest import log_line


def records(*lines):
    return [parse_line(line) for line in lines]


def test_counts_and_error_rate():
    s = summarize(records(
        log_line(status=200),
        log_line(status=200),
        log_line(status=201),
        log_line(status=404),
        log_line(status=500),
    ))

    assert s.requests == 5
    assert s.errors == 2
    assert s.error_rate == 0.4
    assert s.status_classes == {"2xx": 3, "4xx": 1, "5xx": 1}
    assert s.statuses == {200: 2, 201: 1, 404: 1, 500: 1}


def test_top_paths_ignore_query_strings():
    s = summarize(records(
        log_line(request="GET /search?q=boots HTTP/1.1"),
        log_line(request="GET /search?q=socks HTTP/1.1"),
        log_line(request="GET /search HTTP/1.1"),
        log_line(request="GET / HTTP/1.1"),
    ))
    assert s.top_paths == [("/search", 3), ("/", 1)]


def test_top_ips_and_unique_ips():
    s = summarize(records(
        log_line(ip="192.0.2.1"),
        log_line(ip="192.0.2.2"),
        log_line(ip="192.0.2.2"),
        log_line(ip="192.0.2.3"),
        log_line(ip="192.0.2.3"),
        log_line(ip="192.0.2.3"),
    ), top=2)
    assert s.unique_ips == 3
    assert s.top_ips == [("192.0.2.3", 3), ("192.0.2.2", 2)]


def test_bytes_and_slow_requests():
    s = summarize(records(
        log_line(size=100, request_time=0.2),
        log_line(size=250, request_time=1.5),
        log_line(size=50, request_time=None),
    ))
    assert s.bytes_sent == 400
    assert s.slow_requests == 1


def test_first_and_last_seen_handle_out_of_order_lines():
    s = summarize(records(
        log_line(time="02/Nov/2025:10:05:00 +0000"),
        log_line(time="02/Nov/2025:10:00:00 +0000"),
        log_line(time="02/Nov/2025:10:10:00 +0000"),
    ))
    assert s.first_seen.minute == 0
    assert s.last_seen.minute == 10


def test_top_n():
    counts = Counter({"/a": 5, "/b": 9, "/c": 1, "/d": 7})
    assert top_n(counts, 2) == [("/b", 9), ("/d", 7)]
    assert top_n(counts, 10) == [("/b", 9), ("/d", 7), ("/a", 5), ("/c", 1)]
