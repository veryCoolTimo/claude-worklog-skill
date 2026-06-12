from worklog.dates import parse_hours

HEADERS = ["Date", "Hours", "What I did", "Project"]


def merge_text(existing: str, new: str) -> str:
    existing = (existing or "").strip()
    new = (new or "").strip()
    if not existing:
        return new
    parts = [p.strip() for p in existing.split(";")]
    if new in parts:
        return existing
    return f"{existing}; {new}"


def upsert(backend, date: str, hours: float, text: str, project: str):
    rows = backend.get_all_values()
    for i, row in enumerate(rows):
        if i == 0:
            continue
        r_date = row[0] if len(row) > 0 else ""
        r_proj = row[3] if len(row) > 3 else ""
        if r_date == date and r_proj == project:
            new_hours = parse_hours(row[1] if len(row) > 1 else 0) + float(hours)
            new_text = merge_text(row[2] if len(row) > 2 else "", text)
            backend.update_row(i, [date, new_hours, new_text, project])
            return ("updated", i)
    backend.append_row([date, float(hours), text, project])
    return ("created", len(rows))
