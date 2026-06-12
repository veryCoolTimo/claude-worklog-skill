from worklog.dates import parse_hours, format_hours, today_str


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
