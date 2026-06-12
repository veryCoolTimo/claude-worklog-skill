import pytest


@pytest.fixture
def worklog_home(tmp_path, monkeypatch):
    home = tmp_path / "worklog_home"
    home.mkdir()
    monkeypatch.setenv("WORKLOG_HOME", str(home))
    return home
