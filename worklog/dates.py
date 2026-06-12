from datetime import date


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
