from datetime import datetime, timezone

import pytest

from logscope.filters import RecordFilter, StatusMatcher, glob_to_regex
from logscope.parser import parse_line
from logscope.timeparse import parse_when

from .conftest import NOW, log_line


def at(time: str, **kwargs):
    return parse_line(log_line(time=time, **kwargs))


class TestStatusMatcher:
    def test_exact_and_class(self):
        m = StatusMatcher.parse("4xx,500")
        assert m(404) and m(429) and m(500)
        assert not m(200) and not m(502)

    def test_case_and_spaces(self):
        assert StatusMatcher.parse(" 5XX ")(503)

    @pytest.mark.parametrize("spec", ["", "6xx", "40", "abc", "4x"])
    def test_rejects_bad_specs(self, spec):
        with pytest.raises(ValueError):
            StatusMatcher.parse(spec)


class TestGlob:
    def test_star_stays_within_a_segment(self):
        r = glob_to_regex("/products/*")
        assert r.fullmatch("/products/12")
        assert not r.fullmatch("/products/12/reviews")

    def test_double_star_crosses_segments(self):
        r = glob_to_regex("/static/**/*.js")
        assert r.fullmatch("/static/app.js")
        assert r.fullmatch("/static/js/vendor/react.js")
        assert not r.fullmatch("/static/app.json")

    def test_trailing_double_star(self):
        r = glob_to_regex("/api/**")
        assert r.fullmatch("/api/v1/orders")
        assert not r.fullmatch("/apiary")

    def test_question_mark_and_literals(self):
        r = glob_to_regex("/v?/items.json")
        assert r.fullmatch("/v1/items.json")
        assert not r.fullmatch("/v1/itemsXjson")


class TestParseWhen:
    def test_relative(self):
        assert parse_when("2h", NOW) == datetime(2025, 11, 2, 10, 0, tzinfo=timezone.utc)
        assert parse_when("30m", NOW) == datetime(2025, 11, 2, 11, 30, tzinfo=timezone.utc)

    def test_iso_with_offset(self):
        assert parse_when("2025-11-02T06:00:00Z", NOW) == datetime(2025, 11, 2, 6, 0, tzinfo=timezone.utc)

    def test_iso_without_offset_is_utc(self):
        assert parse_when("2025-11-02 06:00", NOW).tzinfo == timezone.utc

    def test_garbage(self):
        with pytest.raises(ValueError):
            parse_when("last tuesday", NOW)


class TestRecordFilter:
    def test_since_is_inclusive_until_is_exclusive(self):
        f = RecordFilter(
            since=parse_when("2025-11-02T10:00:00Z", NOW),
            until=parse_when("2025-11-02T11:00:00Z", NOW),
        )
        assert f.matches(at("02/Nov/2025:10:00:00 +0000"))
        assert f.matches(at("02/Nov/2025:10:59:59 +0000"))
        assert not f.matches(at("02/Nov/2025:11:00:00 +0000"))
        assert not f.matches(at("02/Nov/2025:09:59:59 +0000"))

    def test_relative_since(self):
        f = RecordFilter(since=parse_when("2h", NOW))
        assert f.matches(at("02/Nov/2025:10:30:00 +0000"))
        assert not f.matches(at("02/Nov/2025:09:30:00 +0000"))

    def test_status_and_path_combine(self):
        f = RecordFilter(status=StatusMatcher.parse("5xx"), path=glob_to_regex("/api/**"))
        assert f.matches(at("02/Nov/2025:10:00:00 +0000", status=502, request="POST /api/v1/orders HTTP/1.1"))
        assert not f.matches(at("02/Nov/2025:10:00:00 +0000", status=200, request="POST /api/v1/orders HTTP/1.1"))
        assert not f.matches(at("02/Nov/2025:10:00:00 +0000", status=502, request="GET / HTTP/1.1"))

    def test_path_filter_ignores_query_string(self):
        f = RecordFilter(path=glob_to_regex("/search"))
        assert f.matches(at("02/Nov/2025:10:00:00 +0000", request="GET /search?q=boots HTTP/1.1"))
