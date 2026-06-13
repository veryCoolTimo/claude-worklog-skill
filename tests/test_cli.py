import json

from worklog import cli, store
from worklog.layout import parse_entries
from worklog.sheets import FakeBackend


def test_add_batch_writes_all_entries_atomically(worklog_home, capsys, monkeypatch):
    backend = FakeBackend()
    payload = json.dumps([
        {"date": "02.05.2026", "hours": 2, "text": "a"},
        {"date": "04.05.2026", "hours": 3, "text": "b"},
        {"date": "07.05.2026", "hours": "1.5", "text": "c"},
    ])
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO(payload))
    rc = cli.main(["add-batch", "--project", "Golos CRM"], backend=backend)
    assert rc == 0
    entries = parse_entries(backend.get_all_values())
    assert {e["date"] for e in entries} == {"02.05.2026", "04.05.2026", "07.05.2026"}
    assert all(e["project"] == "Golos CRM" for e in entries)


def test_add_batch_dry_run_does_not_write(worklog_home, capsys, monkeypatch):
    backend = FakeBackend()
    payload = json.dumps([{"date": "02.05.2026", "hours": 2, "text": "a", "project": "P"}])
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO(payload))
    rc = cli.main(["add-batch", "--dry-run"], backend=backend)
    assert rc == 0
    assert backend.get_all_values() == [["Date", "Hours", "What I did", "Project"]]
    assert "dry-run" in capsys.readouterr().out


def test_set_single_overwrites_existing_row(worklog_home, capsys):
    backend = FakeBackend()
    cli.main(["add", "--project", "P", "--hours", "4", "--text", "dup; dup",
              "--date", "02.05.2026"], backend=backend)
    rc = cli.main(["set", "--project", "P", "--hours", "2", "--text", "clean",
                   "--date", "02.05.2026"], backend=backend)
    assert rc == 0
    entries = parse_entries(backend.get_all_values())
    assert len(entries) == 1
    assert entries[0]["hours"] == 2.0 and entries[0]["text"] == "clean"
    assert "set" in capsys.readouterr().out


def test_set_batch_repairs_many_rows(worklog_home, capsys, monkeypatch):
    backend = FakeBackend()
    cli.main(["add", "--project", "Golos CRM", "--hours", "4", "--text", "a; a",
              "--date", "02.05.2026"], backend=backend)
    cli.main(["add", "--project", "Golos CRM", "--hours", "6", "--text", "b; b",
              "--date", "04.05.2026"], backend=backend)
    payload = json.dumps([
        {"date": "02.05.2026", "hours": 2, "text": "a"},
        {"date": "04.05.2026", "hours": 3, "text": "b"},
    ])
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO(payload))
    rc = cli.main(["set", "--project", "Golos CRM"], backend=backend)
    assert rc == 0
    by_date = {e["date"]: e for e in parse_entries(backend.get_all_values())}
    assert by_date["02.05.2026"]["hours"] == 2.0 and by_date["02.05.2026"]["text"] == "a"
    assert by_date["04.05.2026"]["hours"] == 3.0 and by_date["04.05.2026"]["text"] == "b"


def test_add_batch_buffers_all_when_backend_fails(worklog_home, capsys, monkeypatch):
    def boom(cfg=None):
        raise RuntimeError("no network")

    payload = json.dumps([
        {"date": "02.05.2026", "hours": 2, "text": "a", "project": "P"},
        {"date": "04.05.2026", "hours": 3, "text": "b", "project": "P"},
    ])
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO(payload))
    rc = cli.main(["add-batch"], backend_factory=boom)
    assert rc == 0
    assert len(store.read_pending()) == 2
    assert "buffered" in capsys.readouterr().out.lower()


def test_add_creates_formatted_sheet(worklog_home, capsys):
    backend = FakeBackend()
    rc = cli.main(
        ["add", "--project", "content.fans", "--hours", "2", "--text", "did X",
         "--date", "12.06.2026"],
        backend=backend,
    )
    assert rc == 0
    col0 = [r[0] for r in backend.get_all_values()]
    assert "JUNE 2026" in col0
    assert "GRAND TOTAL" in col0
    entries = parse_entries(backend.get_all_values())
    assert entries[0] == {"date": "12.06.2026", "hours": 2.0, "text": "did X", "project": "content.fans"}
    assert "created" in capsys.readouterr().out


def test_add_dry_run_does_not_write(worklog_home, capsys):
    backend = FakeBackend()
    rc = cli.main(
        ["add", "--project", "p", "--hours", "1", "--text", "y", "--date", "12.06.2026",
         "--dry-run"],
        backend=backend,
    )
    assert rc == 0
    assert backend.get_all_values() == [["Date", "Hours", "What I did", "Project"]]
    assert "dry-run" in capsys.readouterr().out


def test_add_buffers_when_backend_factory_fails(worklog_home, capsys):
    def boom(cfg=None):
        raise RuntimeError("no network")

    rc = cli.main(
        ["add", "--project", "p", "--hours", "1", "--text", "y", "--date", "12.06.2026"],
        backend_factory=boom,
    )
    assert rc == 0
    pending = store.read_pending()
    assert len(pending) == 1 and pending[0]["text"] == "y"
    assert "buffered" in capsys.readouterr().out.lower()


def test_flush_replays_pending(worklog_home, capsys):
    store.buffer_entry({"date": "12.06.2026", "hours": 1.0, "text": "y", "project": "p"})
    backend = FakeBackend()
    rc = cli.main(["flush"], backend=backend)
    assert rc == 0
    entries = parse_entries(backend.get_all_values())
    assert entries[0]["text"] == "y"
    assert store.read_pending() == []


def test_show_prints_only_rows_for_date(worklog_home, capsys):
    backend = FakeBackend()
    cli.main(["add", "--project", "p", "--hours", "1", "--text", "today",
              "--date", "12.06.2026"], backend=backend)
    cli.main(["add", "--project", "p", "--hours", "1", "--text", "yesterday",
              "--date", "11.06.2026"], backend=backend)
    capsys.readouterr()  # clear
    cli.main(["show", "--date", "12.06.2026"], backend=backend)
    out = capsys.readouterr().out
    assert "today" in out and "yesterday" not in out


def test_init_subcommand(worklog_home, tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc = cli.main(["init", "content.fans"])
    assert rc == 0
    assert (tmp_path / ".claude" / "worklog.local.json").exists()
