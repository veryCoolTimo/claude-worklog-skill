"""Single-sheet timesheet layout.

The data rows are the single source of truth. On every write we parse the data
rows out of the sheet (rows whose first cell is a DD.MM.YYYY date), merge the new
entry, then regenerate the entire formatted sheet — month headers, monthly totals,
and a grand total — and overwrite. No fragile in-place row insertion.
"""
import re
from itertools import groupby

from worklog.core import HEADERS, merge_text
from worklog.dates import parse_hours, parse_date, date_key, month_header, month_total_label

DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")


def parse_entries(rows):
    entries = []
    for row in rows or []:
        c0 = (row[0] if len(row) > 0 else "") or ""
        c0 = c0.strip()
        if DATE_RE.match(c0):
            entries.append(
                {
                    "date": c0,
                    "hours": parse_hours(row[1] if len(row) > 1 else 0),
                    "text": (row[2] if len(row) > 2 else "") or "",
                    "project": (row[3] if len(row) > 3 else "") or "",
                }
            )
    return entries


def upsert_entries(entries, date, hours, text, project):
    for e in entries:
        if e["date"] == date and e["project"] == project:
            e["hours"] = round(e["hours"] + float(hours), 2)
            e["text"] = merge_text(e["text"], text)
            return "updated"
    entries.append({"date": date, "hours": float(hours), "text": text, "project": project})
    return "created"


def render(entries):
    out = [HEADERS[:]]
    ordered = sorted(entries, key=lambda e: (date_key(e["date"]), e["project"]))
    grand_hours = 0.0
    grand_days = set()
    for (year, month), group in groupby(ordered, key=lambda e: parse_date(e["date"])[:2]):
        group = list(group)
        out.append([month_header(year, month), "", "", ""])
        month_hours = 0.0
        month_days = set()
        for e in group:
            out.append([e["date"], e["hours"], e["text"], e["project"]])
            month_hours += e["hours"]
            month_days.add(e["date"])
        grand_hours += month_hours
        grand_days |= month_days
        out.append([month_total_label(month), round(month_hours, 2), f"{len(month_days)} days", ""])
    out.append(["GRAND TOTAL", round(grand_hours, 2), f"{len(grand_days)} active days", ""])
    return out


def record(backend, date, hours, text, project):
    """Read sheet, merge one entry, regenerate the full formatted layout, write back."""
    entries = parse_entries(backend.get_all_values())
    action = upsert_entries(entries, date, float(hours), text, project)
    backend.replace_all(render(entries))
    return action
