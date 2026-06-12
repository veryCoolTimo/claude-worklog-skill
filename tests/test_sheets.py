from worklog.core import HEADERS, upsert
from worklog.sheets import FakeBackend


def test_fake_backend_starts_with_header():
    b = FakeBackend()
    assert b.get_all_values() == [HEADERS]


def test_fake_backend_supports_upsert_roundtrip():
    b = FakeBackend()
    upsert(b, "12.06.2026", 2.0, "did X", "content.fans")
    vals = b.get_all_values()
    assert vals[1] == ["12.06.2026", 2.0, "did X", "content.fans"]


def test_fake_backend_seeded_rows():
    seed = [HEADERS[:], ["11.06.2026", 1.0, "old", "p"]]
    b = FakeBackend(seed)
    assert len(b.get_all_values()) == 2
