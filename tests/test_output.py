from logscope.output import millis, percent, table


def test_table_aligns_columns():
    text = table(["Path", "Requests"], [["/", 12], ["/products", 3]], right=[1])
    assert text.splitlines() == [
        "Path       Requests",
        "---------  --------",
        "/                12",
        "/products         3",
    ]


def test_formatters():
    assert percent(0.0512) == "5.1%"
    assert millis(0.0004) == "0 ms"
    assert millis(12.3456) == "12,346 ms"
