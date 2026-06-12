from worklog import cli, store
from worklog.sheets import FakeBackend


def test_add_creates_row_with_injected_backend(worklog_home, capsys):
    backend = FakeBackend()
    rc = cli.main(
        ["add", "--project", "content.fans", "--hours", "2", "--text", "did X",
         "--date", "12.06.2026"],
        backend=backend,
    )
    assert rc == 0
    assert backend.rows[1] == ["12.06.2026", 2.0, "did X", "content.fans"]
    out = capsys.readouterr().out
    assert "created" in out


def test_add_dry_run_does_not_write(worklog_home, capsys):
    backend = FakeBackend()
    rc = cli.main(
        ["add", "--project", "p", "--hours", "1", "--text", "y", "--date", "12.06.2026",
         "--dry-run"],
        backend=backend,
    )
    assert rc == 0
    assert len(backend.rows) == 1  # header only
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
    assert backend.rows[1] == ["12.06.2026", 1.0, "y", "p"]
    assert store.read_pending() == []


def test_init_subcommand(worklog_home, tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc = cli.main(["init", "content.fans"])
    assert rc == 0
    assert (tmp_path / ".claude" / "worklog.local.json").exists()
