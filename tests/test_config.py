from worklog import config


def test_config_dir_honors_env(worklog_home):
    assert config.config_dir() == worklog_home


def test_load_returns_defaults_when_missing(worklog_home):
    cfg = config.load_config()
    assert cfg["log_tab"] == "Log"
    assert cfg["spreadsheet_id"] == ""
    assert cfg["aliases"] == {}
    assert cfg["known_projects"] == []


def test_save_then_load_roundtrip(worklog_home):
    cfg = config.load_config()
    cfg["spreadsheet_id"] = "SHEET123"
    cfg["known_projects"].append("content.fans")
    config.save_config(cfg)
    again = config.load_config()
    assert again["spreadsheet_id"] == "SHEET123"
    assert again["known_projects"] == ["content.fans"]
    assert again["log_tab"] == "Log"
