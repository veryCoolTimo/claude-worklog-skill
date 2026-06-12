from worklog.dates import (
    parse_hours,
    format_hours,
    today_str,
    parse_date,
    month_header,
    month_total_label,
)


def test_parse_hours_accepts_dot_comma_int_float_empty():
    assert parse_hours("0.5") == 0.5
    assert parse_hours("0,5") == 0.5
    assert parse_hours("2") == 2.0
    assert parse_hours(3.0) == 3.0
    assert parse_hours("") == 0.0
    assert parse_hours(None) == 0.0


def test_format_hours_drops_trailing_zero():
    assert format_hours(2.0) == "2"
    assert format_hours(0.5) == "0.5"
    assert format_hours(1.5) == "1.5"


def test_today_str_is_ddmmyyyy():
    s = today_str()
    assert len(s) == 10 and s[2] == "." and s[5] == "."


def test_parse_date():
    assert parse_date("06.03.2026") == (2026, 3, 6)


def test_month_header_and_total_label():
    assert month_header(2026, 3) == "MARCH 2026"
    assert month_header(2026, 4) == "APRIL 2026"
    assert month_total_label(3) == "March total"
