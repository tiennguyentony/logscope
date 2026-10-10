from datetime import timedelta

import pytest

from logscope.parser import parse_line, parse_time, split_request, strip_query

from .conftest import log_line


def test_parses_a_combined_line_with_request_time():
    r = parse_line(log_line(request="GET /products/12?ref=home HTTP/2.0", status=200, size=2048, request_time=0.123))

    assert r is not None
    assert r.ip == "192.0.2.1"
    assert r.user is None
    assert r.method == "GET"
    assert r.target == "/products/12?ref=home"
    assert r.path == "/products/12"
    assert r.protocol == "HTTP/2.0"
    assert r.status == 200
    assert r.status_class == "2xx"
    assert r.bytes_sent == 2048
    assert r.referer is None
    assert r.request_time == pytest.approx(0.123)


def test_request_time_is_optional():
    r = parse_line(log_line(request_time=None))
    assert r is not None
    assert r.request_time is None


def test_dash_bytes_means_zero():
    r = parse_line(log_line(status=304, size="-"))
    assert r.bytes_sent == 0


def test_keeps_the_logged_offset():
    r = parse_line(log_line(time="02/Nov/2025:01:30:00 -0500"))
    assert r.time.hour == 1
    assert r.time.utcoffset() == timedelta(hours=-5)


def test_remote_user_is_kept():
    r = parse_line(log_line(user="alice"))
    assert r.user == "alice"


def test_line_endings_are_stripped_from_raw():
    line = log_line()
    r = parse_line(line + "\r\n")
    assert r.raw == line


@pytest.mark.parametrize("line", ["", "garbage", "192.0.2.1 - - [yesterday] \"GET / HTTP/1.1\" 200 1 \"-\" \"-\""])
def test_returns_none_for_lines_that_are_not_access_log_lines(line):
    assert parse_line(line) is None


def test_bad_month_is_rejected():
    with pytest.raises(ValueError):
        parse_time("02/Foo/2025:01:30:00 +0000")


def test_junk_request_keeps_the_raw_request_as_target():
    assert split_request(r"\x16\x03\x01") == ("-", r"\x16\x03\x01", "-")


def test_strip_query():
    assert strip_query("/search?q=boots&page=2") == "/search"
    assert strip_query("/search") == "/search"


# TODO: add IPv6 and app user-agent cases once we have real lines from the
# load balancer; the ones in samples/ are generated.
