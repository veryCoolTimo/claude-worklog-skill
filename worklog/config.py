import copy
import json
import os
from pathlib import Path

DEFAULTS = {
    "spreadsheet_id": "",
    "log_tab": "Log",
    "aliases": {},
    "known_projects": [],
}


def config_dir() -> Path:
    env = os.environ.get("WORKLOG_HOME")
    return Path(env) if env else Path.home() / ".config" / "worklog"


def config_path() -> Path:
    return config_dir() / "config.json"


def service_account_path() -> Path:
    return config_dir() / "service-account.json"


def pending_path() -> Path:
    return config_dir() / "pending.jsonl"


def load_config() -> dict:
    path = config_path()
    cfg = copy.deepcopy(DEFAULTS)
    if path.exists():
        cfg.update(json.loads(path.read_text(encoding="utf-8")))
    for key, value in DEFAULTS.items():
        if key not in cfg:
            cfg[key] = copy.deepcopy(value)
    return cfg


def save_config(cfg: dict) -> None:
    d = config_dir()
    d.mkdir(parents=True, exist_ok=True)
    config_path().write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
    )
