from datetime import date

MONTHS = [
    "",
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def today_str() -> str:
    return date.today().strftime("%d.%m.%Y")


def parse_hours(value) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return float(str(value).strip().replace(",", "."))


def format_hours(value: float) -> str:
    f = float(value)
    if f.is_integer():
        return str(int(f))
    return "%g" % f


def parse_date(s: str):
    """'DD.MM.YYYY' -> (year, month, day) ints."""
    d, m, y = str(s).strip().split(".")
    return (int(y), int(m), int(d))


def date_key(s: str):
    return parse_date(s)


def month_header(year: int, month: int) -> str:
    """e.g. (2026, 3) -> 'MARCH 2026'."""
    return f"{MONTHS[month].upper()} {year}"


def month_total_label(month: int) -> str:
    """e.g. 3 -> 'March total'."""
    return f"{MONTHS[month]} total"
