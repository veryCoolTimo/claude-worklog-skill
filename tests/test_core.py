from worklog.core import HEADERS, merge_text, upsert


class ListBackend:
    def __init__(self, rows=None):
        self.rows = rows or [HEADERS[:]]

    def get_all_values(self):
        return [r[:] for r in self.rows]

    def append_row(self, row):
        self.rows.append(row)

    def update_row(self, idx, row):
        self.rows[idx] = row


def test_upsert_creates_new_row():
    b = ListBackend()
    action, idx = upsert(b, "12.06.2026", 2.0, "did X", "content.fans")
    assert action == "created"
    assert b.rows[idx] == ["12.06.2026", 2.0, "did X", "content.fans"]


def test_upsert_accumulates_same_day_same_project():
    b = ListBackend()
    upsert(b, "12.06.2026", 2.0, "did X", "content.fans")
    action, idx = upsert(b, "12.06.2026", 1.5, "did Y", "content.fans")
    assert action == "updated"
    assert b.rows[idx][1] == 3.5
    assert b.rows[idx][2] == "did X; did Y"
    assert len(b.rows) == 2  # header + one merged row


def test_upsert_separate_rows_for_different_project_same_day():
    b = ListBackend()
    upsert(b, "12.06.2026", 2.0, "did X", "content.fans")
    upsert(b, "12.06.2026", 1.0, "did Z", "TruckingBrief")
    assert len(b.rows) == 3


def test_merge_text_skips_exact_duplicate():
    assert merge_text("did X", "did X") == "did X"
    assert merge_text("did X", "did Y") == "did X; did Y"
    assert merge_text("", "did X") == "did X"
