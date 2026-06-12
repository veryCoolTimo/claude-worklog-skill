from worklog import cli, store
from worklog.layout import parse_entries
from worklog.sheets import FakeBackend


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
