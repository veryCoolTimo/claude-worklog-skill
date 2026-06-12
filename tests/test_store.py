from worklog import store


def test_buffer_then_read(worklog_home):
    store.buffer_entry({"date": "12.06.2026", "hours": 2.0, "text": "x", "project": "p"})
    store.buffer_entry({"date": "12.06.2026", "hours": 1.0, "text": "y", "project": "p"})
    pending = store.read_pending()
    assert len(pending) == 2
    assert pending[0]["text"] == "x"


def test_clear_pending(worklog_home):
    store.buffer_entry({"date": "12.06.2026", "hours": 2.0, "text": "x", "project": "p"})
    store.clear_pending()
    assert store.read_pending() == []
