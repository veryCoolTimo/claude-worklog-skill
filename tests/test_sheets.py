from worklog.core import HEADERS
from worklog.layout import record, parse_entries
from worklog.sheets import FakeBackend


def test_fake_backend_starts_with_header():
    b = FakeBackend()
    assert b.get_all_values() == [HEADERS]


def test_fake_backend_replace_all():
    b = FakeBackend()
    b.replace_all([HEADERS, ["12.06.2026", 1.0, "x", "p"]])
    assert b.get_all_values()[1] == ["12.06.2026", 1.0, "x", "p"]


def test_record_roundtrip_through_fake_backend():
    b = FakeBackend()
    record(b, "12.06.2026", 2.0, "did X", "content.fans")
    entries = parse_entries(b.get_all_values())
    assert len(entries) == 1
    assert entries[0]["date"] == "12.06.2026"
    assert entries[0]["hours"] == 2.0
    assert entries[0]["project"] == "content.fans"
