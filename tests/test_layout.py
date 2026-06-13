from worklog.core import HEADERS
from worklog.layout import parse_entries, upsert_entries, render, record, record_many
from worklog.sheets import FakeBackend


def test_record_many_writes_all_entries_in_one_pass():
    b = FakeBackend()
    items = [
        {"date": "02.05.2026", "hours": 2, "text": "a", "project": "P"},
        {"date": "04.05.2026", "hours": 3, "text": "b", "project": "P"},
        {"date": "07.05.2026", "hours": 1.5, "text": "c", "project": "P"},
    ]
    actions = record_many(b, items)
    assert [a for a, _ in actions] == ["created", "created", "created"]
    entries = parse_entries(b.get_all_values())
    assert len(entries) == 3
    assert {e["date"] for e in entries} == {"02.05.2026", "04.05.2026", "07.05.2026"}


def test_set_entries_overwrites_instead_of_accumulating():
    from worklog.layout import set_entries
    entries = [{"date": "02.05.2026", "hours": 4.0, "text": "x; x", "project": "P"}]
    action = set_entries(entries, "02.05.2026", 2.0, "x", "P")
    assert action == "set"
    assert len(entries) == 1
    assert entries[0]["hours"] == 2.0
    assert entries[0]["text"] == "x"


def test_record_many_set_mode_repairs_doubled_rows():
    b = FakeBackend()
    # simulate a doubled row plus an unrelated same-date row for another project
    record(b, "02.05.2026", 4.0, "dup; dup", "Golos CRM")
    record(b, "02.05.2026", 1.0, "support", "Support")
    record_many(b, [{"date": "02.05.2026", "hours": 2.0, "text": "clean", "project": "Golos CRM"}], mode="set")
    by_key = {(e["date"], e["project"]): e for e in parse_entries(b.get_all_values())}
    assert by_key[("02.05.2026", "Golos CRM")]["hours"] == 2.0
    assert by_key[("02.05.2026", "Golos CRM")]["text"] == "clean"
    assert by_key[("02.05.2026", "Support")]["hours"] == 1.0  # untouched


def test_record_many_preserves_existing_rows_and_accumulates():
    b = FakeBackend()
    record(b, "01.06.2026", 1.0, "pre-existing", "P")
    record_many(b, [
        {"date": "02.05.2026", "hours": 2, "text": "new", "project": "P"},
        {"date": "01.06.2026", "hours": 0.5, "text": "more", "project": "P"},  # same key -> accumulates
    ])
    entries = {(e["date"], e["project"]): e for e in parse_entries(b.get_all_values())}
    assert len(entries) == 2
    assert entries[("01.06.2026", "P")]["hours"] == 1.5
    assert entries[("01.06.2026", "P")]["text"] == "pre-existing; more"
    assert entries[("02.05.2026", "P")]["hours"] == 2.0


def test_render_single_entry_has_month_header_and_totals():
    rows = render([{"date": "06.03.2026", "hours": 0.5, "text": "x", "project": "TB"}])
    assert rows[0] == HEADERS
    assert rows[1] == ["MARCH 2026", "", "", ""]
    assert rows[2] == ["06.03.2026", 0.5, "x", "TB"]
    assert rows[3] == ["March total", 0.5, "1 days", ""]
    assert rows[4] == ["GRAND TOTAL", 0.5, "1 active days", ""]


def test_render_groups_two_months_and_counts_active_days():
    entries = [
        {"date": "06.03.2026", "hours": 0.5, "text": "a", "project": "TB"},
        {"date": "13.03.2026", "hours": 3, "text": "b", "project": "TB"},
        {"date": "01.04.2026", "hours": 1, "text": "c", "project": "cf"},
    ]
    rows = render(entries)
    col0 = [r[0] for r in rows]
    assert "MARCH 2026" in col0 and "APRIL 2026" in col0
    march = rows[col0.index("March total")]
    assert march[1] == 3.5 and march[2] == "2 days"
    grand = rows[col0.index("GRAND TOTAL")]
    assert grand[1] == 4.5 and grand[2] == "3 active days"


def test_active_days_counts_distinct_dates_not_rows():
    entries = [
        {"date": "06.03.2026", "hours": 1, "text": "a", "project": "P1"},
        {"date": "06.03.2026", "hours": 1, "text": "b", "project": "P2"},
    ]
    rows = render(entries)
    col0 = [r[0] for r in rows]
    march = rows[col0.index("March total")]
    assert march[1] == 2.0
    assert march[2] == "1 days"  # same date, two projects -> 1 active day


def test_parse_entries_ignores_headers_and_totals():
    rows = render([{"date": "06.03.2026", "hours": 1, "text": "a", "project": "P"}])
    entries = parse_entries(rows)
    assert len(entries) == 1
    assert entries[0]["project"] == "P"


def test_upsert_entries_accumulates_same_day_same_project():
    entries = []
    assert upsert_entries(entries, "06.03.2026", 1.0, "a", "P") == "created"
    assert upsert_entries(entries, "06.03.2026", 0.5, "b", "P") == "updated"
    assert len(entries) == 1
    assert entries[0]["hours"] == 1.5
    assert entries[0]["text"] == "a; b"


def test_record_accumulates_in_place_through_backend():
    b = FakeBackend()
    record(b, "06.03.2026", 1.0, "a", "P")
    action = record(b, "06.03.2026", 0.5, "b", "P")
    assert action == "updated"
    entries = parse_entries(b.get_all_values())
    assert len(entries) == 1
    assert entries[0]["hours"] == 1.5
    assert entries[0]["text"] == "a; b"


def test_record_keeps_months_chronological_regardless_of_write_order():
    b = FakeBackend()
    record(b, "01.04.2026", 1.0, "april", "P")
    record(b, "06.03.2026", 2.0, "march", "P")  # earlier month written later
    col0 = [r[0] for r in b.get_all_values()]
    assert col0.index("MARCH 2026") < col0.index("APRIL 2026")
    # grand total reflects both
    grand = b.get_all_values()[col0.index("GRAND TOTAL")]
    assert grand[1] == 3.0 and grand[2] == "2 active days"
