import pytest

from logscope.latency import latency_report
from logscope.parser import parse_line

from .conftest import log_line


def records(*specs):
    return [parse_line(log_line(request=f"GET {path} HTTP/1.1", request_time=t)) for path, t in specs]


def test_overall_percentiles_and_mean():
    report = latency_report(
        records(("/", 0.1), ("/", 0.2), ("/", 0.3), ("/a", 0.4), ("/a", 0.5)),
        ps=[50, 99],
    )
    assert report.requests == 5
    assert report.untimed == 0
    assert report.overall.count == 5
    assert report.overall.mean == pytest.approx(0.3)
    assert report.overall.max == 0.5
    assert report.overall.percentiles == {50: 0.3, 99: 0.5}


def test_untimed_lines_are_counted_but_not_used():
    report = latency_report(records(("/", 0.2), ("/", None), ("/", None)), ps=[50])
    assert report.requests == 3
    assert report.untimed == 2
    assert report.overall.count == 1
    assert report.overall.percentiles[50] == 0.2


def test_no_timed_requests():
    report = latency_report(records(("/", None)), ps=[50])
    assert report.overall is None


def test_by_path_busiest_first():
    report = latency_report(
        records(("/a", 0.1), ("/b", 0.2), ("/b", 0.3), ("/c", 0.4), ("/b", 2.0)),
        ps=[50],
        by_path=2,
    )
    assert [path for path, _ in report.by_path] == ["/b", "/a"]
    b = report.by_path[0][1]
    assert b.count == 3
    assert b.slow == 1
