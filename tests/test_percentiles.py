import pytest

from logscope.percentiles import parse_percentiles, percentile

LATENCIES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]


@pytest.mark.parametrize(
    ("p", "expected"),
    [(50, 0.4), (90, 0.7), (99, 0.7), (10, 0.1)],
)
def test_percentile(p, expected):
    assert percentile(LATENCIES, p) == expected


def test_percentile_is_always_an_observed_value():
    values = [0.012, 0.250, 0.031, 1.900, 0.044]
    assert percentile(sorted(values), 75) in values


def test_single_value():
    assert percentile([0.25], 50) == 0.25
    assert percentile([0.25], 99) == 0.25


def test_empty_is_an_error():
    with pytest.raises(ValueError):
        percentile([], 50)


def test_parse_percentiles():
    assert parse_percentiles("50,95,99.9") == [50, 95, 99.9]
    assert parse_percentiles("p50, p99") == [50, 99]


@pytest.mark.parametrize("spec", ["0", "101", "-5", "abc", "50,,99"])
def test_parse_percentiles_rejects_bad_values(spec):
    with pytest.raises(ValueError):
        parse_percentiles(spec)
