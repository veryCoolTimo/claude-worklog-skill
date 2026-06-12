# Worklog Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Code skill that logs work to a Google Sheet timesheet in real time — one row per day per project, with effort-estimate hours and a concise English summary.

**Architecture:** A Python CLI (`worklog`) holds all deterministic logic (upsert by date+project, hours accumulation, project resolution, offline buffering) behind a `SheetBackend` interface so it is unit-testable without Google. A global Claude skill (`SKILL.md`) is the brain that decides project/hours/text and calls the CLI. A lightweight `SessionStart` hook nudges Claude to log in tracked projects. Google auth is a service account.

**Tech Stack:** Python 3.11+, `gspread` (Google Sheets), `google-auth`, `pytest`, argparse. Skill + hook are plain files symlinked into `~/.claude/`.

---

## File Structure

```
claude-worklog-skill/
├── pyproject.toml                 # package + `worklog` console_script
├── config.example.json            # template for ~/.config/worklog/config.json
├── install.sh                     # venv + symlink skill/hook into ~/.claude
├── worklog/
│   ├── __init__.py
│   ├── dates.py                   # today_str, parse_hours, format_hours
│   ├── core.py                    # HEADERS, merge_text, upsert (pure logic)
│   ├── sheets.py                  # FakeBackend, GspreadBackend, open_worksheet
│   ├── config.py                  # config dir/paths, load/save
│   ├── project.py                 # resolve_project, init_project
│   ├── store.py                   # pending.jsonl buffer/flush
│   └── cli.py                     # argparse entrypoint
├── hooks/
│   └── session_start.py           # SessionStart nudge (tracked projects only)
├── skill/
│   └── SKILL.md                   # the worklog skill (the brain)
└── tests/
    ├── conftest.py                # tmp WORKLOG_HOME fixture
    ├── test_dates.py
    ├── test_core.py
    ├── test_config.py
    ├── test_project.py
    ├── test_store.py
    ├── test_cli.py
    └── test_hook.py
```

**Design contracts (used across tasks):**
- `HEADERS = ["Date", "Hours", "What I did", "Project"]`
- Sheet row = `[date_str, hours_float, text_str, project_str]`. `date_str` is `DD.MM.YYYY`.
- Backend interface: `get_all_values() -> list[list]`, `append_row(row: list) -> None`, `update_row(idx: int, row: list) -> None` (`idx` 0-based, includes header at 0).
- `upsert(backend, date, hours, text, project) -> tuple[str, int]` returns `("created"|"updated", idx)`.
- Config dir = `$WORKLOG_HOME` or `~/.config/worklog` (env override makes tests hermetic).

---

### Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`, `worklog/__init__.py`, `tests/conftest.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "worklog"
version = "0.1.0"
description = "Claude Code skill engine: log work to a Google Sheet timesheet"
requires-python = ">=3.11"
dependencies = ["gspread>=6.0", "google-auth>=2.0"]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[project.scripts]
worklog = "worklog.cli:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["worklog*"]
```

- [ ] **Step 2: Create empty `worklog/__init__.py`**

```python
__version__ = "0.1.0"
```

- [ ] **Step 3: Create `tests/conftest.py` (hermetic config home)**

```python
import os
import pytest


@pytest.fixture
def worklog_home(tmp_path, monkeypatch):
    home = tmp_path / "worklog_home"
    home.mkdir()
    monkeypatch.setenv("WORKLOG_HOME", str(home))
    return home
```

- [ ] **Step 4: Create venv and install**

Run: `python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"`
Expected: installs gspread, google-auth, pytest; `worklog` command available.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml worklog/__init__.py tests/conftest.py
git commit -m "chore: scaffold worklog package and test harness"
```

---

### Task 2: Dates and hours utilities

**Files:**
- Create: `worklog/dates.py`, `tests/test_dates.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_dates.py
from worklog.dates import parse_hours, format_hours, today_str


def test_parse_hours_accepts_dot_comma_int_float_empty():
    assert parse_hours("0.5") == 0.5
    assert parse_hours("0,5") == 0.5
    assert parse_hours("2") == 2.0
    assert parse_hours(3.0) == 3.0
    assert parse_hours("") == 0.0
    assert parse_hours(None) == 0.0


def test_format_hours_drops_trailing_zero():
    assert format_hours(2.0) == "2"
    assert format_hours(0.5) == "0.5"
    assert format_hours(1.5) == "1.5"


def test_today_str_is_ddmmyyyy():
    s = today_str()
    assert len(s) == 10 and s[2] == "." and s[5] == "."
```

- [ ] **Step 2: Run to verify fail**

Run: `pytest tests/test_dates.py -v`
Expected: FAIL (module `worklog.dates` not found).

- [ ] **Step 3: Implement `worklog/dates.py`**

```python
from datetime import date


def today_str() -> str:
    return date.today().strftime("%d.%m.%Y")


def parse_hours(value) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return float(str(value).strip().replace(",", "."))


def format_hours(value: float) -> str:
    f = float(value)
    if f.is_integer():
        return str(int(f))
    return ("%g" % f)
```

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/test_dates.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add worklog/dates.py tests/test_dates.py
git commit -m "feat: date and hours parsing/formatting utilities"
```

---

### Task 3: Core upsert logic

**Files:**
- Create: `worklog/core.py`, `tests/test_core.py`
- Uses `FakeBackend` (defined here in test as a minimal list-backed stub; the real one lands in Task 5 — keep this stub local to the test).

- [ ] **Step 1: Write failing tests**

```python
# tests/test_core.py
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
```

- [ ] **Step 2: Run to verify fail**

Run: `pytest tests/test_core.py -v`
Expected: FAIL (module `worklog.core` not found).

- [ ] **Step 3: Implement `worklog/core.py`**

```python
from worklog.dates import parse_hours

HEADERS = ["Date", "Hours", "What I did", "Project"]


def merge_text(existing: str, new: str) -> str:
    existing = (existing or "").strip()
    new = (new or "").strip()
    if not existing:
        return new
    parts = [p.strip() for p in existing.split(";")]
    if new in parts:
        return existing
    return f"{existing}; {new}"


def upsert(backend, date: str, hours: float, text: str, project: str):
    rows = backend.get_all_values()
    for i, row in enumerate(rows):
        if i == 0:
            continue
        r_date = row[0] if len(row) > 0 else ""
        r_proj = row[3] if len(row) > 3 else ""
        if r_date == date and r_proj == project:
            new_hours = parse_hours(row[1] if len(row) > 1 else 0) + float(hours)
            new_text = merge_text(row[2] if len(row) > 2 else "", text)
            backend.update_row(i, [date, new_hours, new_text, project])
            return ("updated", i)
    backend.append_row([date, float(hours), text, project])
    return ("created", len(rows))
```

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/test_core.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add worklog/core.py tests/test_core.py
git commit -m "feat: core upsert logic with same-day accumulation and text merge"
```

---

### Task 4: Config paths and load/save

**Files:**
- Create: `worklog/config.py`, `tests/test_config.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_config.py
import json
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
    # merged over defaults even if file partial
    assert again["log_tab"] == "Log"
```

- [ ] **Step 2: Run to verify fail**

Run: `pytest tests/test_config.py -v`
Expected: FAIL (module `worklog.config` not found).

- [ ] **Step 3: Implement `worklog/config.py`**

```python
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
    cfg = dict(DEFAULTS)
    if path.exists():
        cfg.update(json.loads(path.read_text(encoding="utf-8")))
    for key, value in DEFAULTS.items():
        cfg.setdefault(key, value)
    return cfg


def save_config(cfg: dict) -> None:
    d = config_dir()
    d.mkdir(parents=True, exist_ok=True)
    config_path().write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
```

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/test_config.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add worklog/config.py tests/test_config.py
git commit -m "feat: config dir resolution and load/save with defaults"
```

---

### Task 5: Sheet backends (Fake + gspread)

**Files:**
- Create: `worklog/sheets.py`, `tests/test_sheets.py`

- [ ] **Step 1: Write failing tests (FakeBackend only — gspread path is integration, tested manually)**

```python
# tests/test_sheets.py
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
```

- [ ] **Step 2: Run to verify fail**

Run: `pytest tests/test_sheets.py -v`
Expected: FAIL (module `worklog.sheets` not found).

- [ ] **Step 3: Implement `worklog/sheets.py`**

```python
from worklog.core import HEADERS
from worklog import config


class FakeBackend:
    """In-memory backend for tests and --dry-run."""

    def __init__(self, rows=None):
        self.rows = [r[:] for r in rows] if rows else [HEADERS[:]]

    def get_all_values(self):
        return [r[:] for r in self.rows]

    def append_row(self, row):
        self.rows.append(list(row))

    def update_row(self, idx, row):
        self.rows[idx] = list(row)


class GspreadBackend:
    """Wraps a gspread Worksheet behind the backend interface."""

    def __init__(self, worksheet):
        self.ws = worksheet

    def get_all_values(self):
        return self.ws.get_all_values()

    def append_row(self, row):
        self.ws.append_row(row, value_input_option="USER_ENTERED")

    def update_row(self, idx, row):
        # idx is 0-based incl header; sheet rows are 1-based
        self.ws.update(f"A{idx + 1}:D{idx + 1}", [row], value_input_option="USER_ENTERED")


def open_worksheet(cfg=None):
    """Open the Log worksheet via service-account auth. Raises on missing creds/network."""
    import gspread
    from google.oauth2.service_account import Credentials

    cfg = cfg or config.load_config()
    sa = config.service_account_path()
    if not sa.exists():
        raise FileNotFoundError(f"Service account key not found: {sa}")
    if not cfg.get("spreadsheet_id"):
        raise ValueError("spreadsheet_id is not set in config.json")

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(str(sa), scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(cfg["spreadsheet_id"])
    ws = sheet.worksheet(cfg.get("log_tab", "Log"))
    return GspreadBackend(ws)
```

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/test_sheets.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add worklog/sheets.py tests/test_sheets.py
git commit -m "feat: Fake and gspread sheet backends"
```

---

### Task 6: Project resolution and init

**Files:**
- Create: `worklog/project.py`, `tests/test_project.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_project.py
import json
from worklog import project, config


def test_resolve_from_claude_md(tmp_path):
    (tmp_path / "CLAUDE.md").write_text('# repo\nworklog-project: "content.fans"\n', encoding="utf-8")
    name, source = project.resolve_project(tmp_path, config.DEFAULTS)
    assert name == "content.fans"
    assert source == "claude_md"


def test_resolve_from_local_json(tmp_path):
    d = tmp_path / ".claude"
    d.mkdir()
    (d / "worklog.local.json").write_text('{"project": "TruckingBrief"}', encoding="utf-8")
    name, source = project.resolve_project(tmp_path, config.DEFAULTS)
    assert name == "TruckingBrief"
    assert source == "local_json"


def test_resolve_from_alias_map(tmp_path):
    cfg = dict(config.DEFAULTS)
    cfg["aliases"] = {tmp_path.name: "CU Kazakhstan"}
    name, source = project.resolve_project(tmp_path, cfg)
    assert name == "CU Kazakhstan"
    assert source == "alias"


def test_resolve_unknown_returns_none(tmp_path):
    name, source = project.resolve_project(tmp_path, config.DEFAULTS)
    assert name is None
    assert source == "ask"


def test_init_writes_marker_instruction_localjson_and_config(tmp_path, worklog_home):
    project.init_project(tmp_path, "content.fans", config.load_config())
    claude_md = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert 'worklog-project: "content.fans"' in claude_md
    assert "worklog" in claude_md.lower()  # instruction block present
    local = json.loads((tmp_path / ".claude" / "worklog.local.json").read_text(encoding="utf-8"))
    assert local["project"] == "content.fans"
    assert "content.fans" in config.load_config()["known_projects"]


def test_init_is_idempotent(tmp_path, worklog_home):
    project.init_project(tmp_path, "content.fans", config.load_config())
    project.init_project(tmp_path, "content.fans", config.load_config())
    claude_md = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert claude_md.count('worklog-project: "content.fans"') == 1
    assert config.load_config()["known_projects"].count("content.fans") == 1
```

- [ ] **Step 2: Run to verify fail**

Run: `pytest tests/test_project.py -v`
Expected: FAIL (module `worklog.project` not found).

- [ ] **Step 3: Implement `worklog/project.py`**

```python
import json
import re
from pathlib import Path

from worklog import config

MARKER_RE = re.compile(r'^worklog-project:\s*"?(.+?)"?\s*$', re.MULTILINE)

INSTRUCTION_BLOCK = (
    "\n## Worklog tracking\n\n"
    "This project tracks work hours. Use the `worklog` skill to record substantial "
    "work to the timesheet (semi-automatically at natural breakpoints, or via `/worklog`).\n"
)


def _local_json(cwd: Path) -> Path:
    return cwd / ".claude" / "worklog.local.json"


def resolve_project(cwd: Path, cfg: dict):
    cwd = Path(cwd)
    claude_md = cwd / "CLAUDE.md"
    if claude_md.exists():
        m = MARKER_RE.search(claude_md.read_text(encoding="utf-8"))
        if m:
            return (m.group(1).strip(), "claude_md")
    lj = _local_json(cwd)
    if lj.exists():
        data = json.loads(lj.read_text(encoding="utf-8"))
        if data.get("project"):
            return (data["project"], "local_json")
    aliases = cfg.get("aliases", {})
    if cwd.name in aliases:
        return (aliases[cwd.name], "alias")
    return (None, "ask")


def init_project(cwd: Path, name: str, cfg: dict) -> None:
    cwd = Path(cwd)
    # 1) local json marker
    lj = _local_json(cwd)
    lj.parent.mkdir(parents=True, exist_ok=True)
    lj.write_text(json.dumps({"project": name}, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2) CLAUDE.md marker + instruction (idempotent)
    claude_md = cwd / "CLAUDE.md"
    text = claude_md.read_text(encoding="utf-8") if claude_md.exists() else ""
    marker_line = f'worklog-project: "{name}"'
    if MARKER_RE.search(text):
        text = MARKER_RE.sub(marker_line, text)
    else:
        prefix = text if text.endswith("\n") or text == "" else text + "\n"
        text = prefix + marker_line + "\n"
    if "## Worklog tracking" not in text:
        text = text + INSTRUCTION_BLOCK
    claude_md.write_text(text, encoding="utf-8")

    # 3) register in central config
    if name not in cfg.get("known_projects", []):
        cfg.setdefault("known_projects", []).append(name)
    config.save_config(cfg)
```

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/test_project.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add worklog/project.py tests/test_project.py
git commit -m "feat: hybrid project resolution and init (CLAUDE.md marker + config)"
```

---

### Task 7: Offline pending buffer

**Files:**
- Create: `worklog/store.py`, `tests/test_store.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_store.py
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
```

- [ ] **Step 2: Run to verify fail**

Run: `pytest tests/test_store.py -v`
Expected: FAIL (module `worklog.store` not found).

- [ ] **Step 3: Implement `worklog/store.py`**

```python
import json

from worklog import config


def buffer_entry(entry: dict) -> None:
    path = config.pending_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_pending() -> list:
    path = config.pending_path()
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def clear_pending() -> None:
    path = config.pending_path()
    if path.exists():
        path.unlink()
```

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/test_store.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add worklog/store.py tests/test_store.py
git commit -m "feat: offline pending.jsonl buffer"
```

---

### Task 8: CLI wiring

**Files:**
- Create: `worklog/cli.py`, `tests/test_cli.py`

The CLI injects the backend so tests use `FakeBackend`. `add` resolves project from `--project` or `resolve_project(cwd)`. On `--dry-run`, it prints the intended action without writing. A backend-construction failure buffers the entry to `pending.jsonl`.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cli.py
import json
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
```

- [ ] **Step 2: Run to verify fail**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL (module `worklog.cli` not found).

- [ ] **Step 3: Implement `worklog/cli.py`**

```python
import argparse
import os
from pathlib import Path

from worklog import config, store
from worklog.core import upsert
from worklog.dates import today_str, format_hours, parse_hours
from worklog.project import resolve_project, init_project
from worklog.sheets import FakeBackend, open_worksheet


def _resolve(args_project, cfg):
    if args_project:
        return args_project
    name, _ = resolve_project(Path.cwd(), cfg)
    return name


def _get_backend(backend, backend_factory, cfg):
    if backend is not None:
        return backend
    factory = backend_factory or open_worksheet
    return factory(cfg)


def cmd_add(args, cfg, backend, backend_factory):
    project = _resolve(args.project, cfg)
    if not project:
        print("No project resolved. Run `worklog init \"<Project>\"` or pass --project.")
        return 1
    date = args.date or today_str()
    hours = parse_hours(args.hours)
    entry = {"date": date, "hours": hours, "text": args.text, "project": project}

    if args.dry_run:
        print(f"[dry-run] {date} | {format_hours(hours)} | {args.text} | {project}")
        return 0

    try:
        b = _get_backend(backend, backend_factory, cfg)
    except Exception as exc:  # offline / no creds — never lose data
        store.buffer_entry(entry)
        print(f"Could not reach Google Sheets ({exc}); entry buffered for later flush.")
        return 0

    action, _ = upsert(b, date, hours, args.text, project)
    print(f"{action}: {date} | {format_hours(hours)} | {args.text} | {project}")
    return 0


def cmd_flush(args, cfg, backend, backend_factory):
    pending = store.read_pending()
    if not pending:
        print("Nothing to flush.")
        return 0
    try:
        b = _get_backend(backend, backend_factory, cfg)
    except Exception as exc:
        print(f"Still cannot reach Google Sheets ({exc}); kept {len(pending)} buffered.")
        return 1
    for e in pending:
        upsert(b, e["date"], parse_hours(e["hours"]), e["text"], e["project"])
    store.clear_pending()
    print(f"Flushed {len(pending)} entr{'y' if len(pending) == 1 else 'ies'}.")
    return 0


def cmd_show(args, cfg, backend, backend_factory):
    date = args.date or today_str()
    try:
        b = _get_backend(backend, backend_factory, cfg)
    except Exception as exc:
        print(f"Could not reach Google Sheets ({exc}).")
        return 1
    for row in b.get_all_values()[1:]:
        if row and row[0] == date:
            print(" | ".join(str(c) for c in row))
    return 0


def cmd_projects(args, cfg, backend, backend_factory):
    for p in cfg.get("known_projects", []):
        print(p)
    return 0


def cmd_init(args, cfg, backend, backend_factory):
    init_project(Path.cwd(), args.name, cfg)
    print(f'Initialized worklog tracking for "{args.name}" in {Path.cwd()}')
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="worklog")
    p.add_argument("--dry-run", action="store_true")
    sub = p.add_subparsers(dest="command", required=True)

    pa = sub.add_parser("add")
    pa.add_argument("--project")
    pa.add_argument("--hours", required=True)
    pa.add_argument("--text", required=True)
    pa.add_argument("--date")
    pa.set_defaults(func=cmd_add)

    pi = sub.add_parser("init")
    pi.add_argument("name")
    pi.set_defaults(func=cmd_init)

    ps = sub.add_parser("show")
    ps.add_argument("--date")
    ps.set_defaults(func=cmd_show)

    sub.add_parser("projects").set_defaults(func=cmd_projects)
    sub.add_parser("flush").set_defaults(func=cmd_flush)
    return p


def main(argv=None, backend=None, backend_factory=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    cfg = config.load_config()
    return args.func(args, cfg, backend, backend_factory)
```

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/test_cli.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add worklog/cli.py tests/test_cli.py
git commit -m "feat: worklog CLI (add/init/show/projects/flush) with offline buffering"
```

---

### Task 9: SessionStart hook

**Files:**
- Create: `hooks/session_start.py`, `tests/test_hook.py`

The hook reads the Claude hook JSON from stdin, extracts `cwd`, and prints a nudge **only** if that project is tracked (CLAUDE.md marker or `.claude/worklog.local.json`). Printing to stdout injects the text as context.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_hook.py
import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "hooks" / "session_start.py"


def _run(cwd):
    payload = json.dumps({"cwd": str(cwd), "hook_event_name": "SessionStart"})
    return subprocess.run(
        [sys.executable, str(HOOK)], input=payload, capture_output=True, text=True
    )


def test_hook_silent_in_untracked_project(tmp_path):
    res = _run(tmp_path)
    assert res.stdout.strip() == ""


def test_hook_nudges_in_tracked_project(tmp_path):
    (tmp_path / "CLAUDE.md").write_text('worklog-project: "content.fans"\n', encoding="utf-8")
    res = _run(tmp_path)
    assert "worklog" in res.stdout.lower()
    assert "content.fans" in res.stdout
```

- [ ] **Step 2: Run to verify fail**

Run: `pytest tests/test_hook.py -v`
Expected: FAIL (hook file does not exist → nonzero / empty mismatch).

- [ ] **Step 3: Implement `hooks/session_start.py`**

```python
#!/usr/bin/env python3
"""Claude Code SessionStart hook: nudge to log work in tracked projects."""
import json
import re
import sys
from datetime import date
from pathlib import Path

MARKER_RE = re.compile(r'^worklog-project:\s*"?(.+?)"?\s*$', re.MULTILINE)


def tracked_project(cwd: Path):
    claude_md = cwd / "CLAUDE.md"
    if claude_md.exists():
        m = MARKER_RE.search(claude_md.read_text(encoding="utf-8"))
        if m:
            return m.group(1).strip()
    lj = cwd / ".claude" / "worklog.local.json"
    if lj.exists():
        try:
            data = json.loads(lj.read_text(encoding="utf-8"))
            if data.get("project"):
                return data["project"]
        except Exception:
            return None
    return None


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    cwd = Path(payload.get("cwd", "."))
    project = tracked_project(cwd)
    if not project:
        return 0
    today = date.today().strftime("%d.%m.%Y")
    print(
        f"[worklog] Today is {today}. This is a tracked project ({project}). "
        "If you do substantial work (~1h+) this session, record it to the timesheet "
        "with the `worklog` skill (or `/worklog`) before wrapping up."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/test_hook.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add hooks/session_start.py tests/test_hook.py
git commit -m "feat: SessionStart nudge hook for tracked projects"
```

---

### Task 10: The skill (SKILL.md)

**Files:**
- Create: `skill/SKILL.md`

- [ ] **Step 1: Write `skill/SKILL.md`**

````markdown
---
name: worklog
description: Log work to the Google Sheet timesheet. Use at natural breakpoints after substantial work (~1h+) in a tracked project, on wrap-up phrases ("на сегодня всё", "закоммитил"), or when the user runs /worklog. Records one row per day per project with an effort-estimate in hours and a concise English summary.
---

# Worklog

Record what was accomplished this session into the Google Sheet timesheet via the
`worklog` CLI engine. One row per **day per project**; same-day work accumulates.

## When to act

- The user runs `/worklog` (optionally `/worklog <hours> "<text>"` to override).
- A substantial chunk of work (~1h+) finished in a **tracked** project, and you are at a
  natural breakpoint (commit made, task done, user says they're wrapping up).
- Do NOT log trivial actions (a single tiny edit, answering a question). Minimum 0.5h.

## Steps

1. **Resolve the project.** Run `worklog projects` and check the repo. The engine resolves
   automatically from `CLAUDE.md` → `.claude/worklog.local.json` → folder alias. If it
   prints "No project resolved", ask the user once for the name, then run
   `worklog init "<Name>"` to remember it.
2. **Summarize the work** in one concise English phrase in the user's terse style — name
   concrete things: fixes, deploys, investigations, files. Example style:
   "deployed TB pipeline, fixed broken /api/redirect/, 7-day filter".
3. **Estimate hours** by volume of work (commit count, number/complexity of edits), rounded
   to 0.5. Use the user's override if they gave one.
4. **Show the user the proposed row** and the date, and let them confirm or edit hours/text.
5. **Write it:**
   ```
   worklog add --project "<Project>" --hours <n> --text "<summary>"
   ```
   Use `--dry-run` first if unsure. Date defaults to today (`DD.MM.YYYY`).
6. If the engine says the entry was **buffered** (offline), tell the user; it will flush
   on the next `worklog flush` or next successful `add`.

## Notes

- Hours are an **effort estimate**, not wall-clock. Round to 0.5, minimum 0.5.
- Same project, same day → the engine accumulates hours and appends text. Don't create a
  second row yourself.
- Never edit the `Report` tab or totals — those are formulas.
````

- [ ] **Step 2: Commit**

```bash
git add skill/SKILL.md
git commit -m "feat: worklog skill (SKILL.md) — the decision/summarize brain"
```

---

### Task 11: Installer, config template, and Google setup docs

**Files:**
- Create: `config.example.json`, `install.sh`, `docs/SETUP.md`

- [ ] **Step 1: Create `config.example.json`**

```json
{
  "spreadsheet_id": "PASTE_SPREADSHEET_ID_HERE",
  "log_tab": "Log",
  "aliases": {
    "content-fans-repo-folder": "content.fans"
  },
  "known_projects": []
}
```

- [ ] **Step 2: Create `install.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="${HOME}/.claude"
CONFIG_DIR="${HOME}/.config/worklog"

echo "==> Creating venv and installing the worklog CLI"
python3 -m venv "${REPO}/.venv"
"${REPO}/.venv/bin/pip" install -e "${REPO}"

echo "==> Linking the skill into ${CLAUDE_DIR}/skills/worklog"
mkdir -p "${CLAUDE_DIR}/skills"
ln -sfn "${REPO}/skill" "${CLAUDE_DIR}/skills/worklog"

echo "==> Preparing config dir ${CONFIG_DIR}"
mkdir -p "${CONFIG_DIR}"
[ -f "${CONFIG_DIR}/config.json" ] || cp "${REPO}/config.example.json" "${CONFIG_DIR}/config.json"

echo
echo "Next steps (manual):"
echo "  1. Put your service account key at ${CONFIG_DIR}/service-account.json"
echo "  2. Set spreadsheet_id in ${CONFIG_DIR}/config.json"
echo "  3. Make 'worklog' available on PATH, e.g.:"
echo "       ln -sfn ${REPO}/.venv/bin/worklog /usr/local/bin/worklog"
echo "  4. Register the SessionStart hook in ${CLAUDE_DIR}/settings.json (see docs/SETUP.md)"
```

- [ ] **Step 3: Create `docs/SETUP.md` (the "Google at the end" checklist)**

```markdown
# Worklog setup

## 1. Google Cloud service account
1. https://console.cloud.google.com → create / pick a project.
2. APIs & Services → Library → enable **Google Sheets API**.
3. APIs & Services → Credentials → Create credentials → **Service account**.
4. Open the service account → Keys → Add key → JSON → download.
5. Save it as `~/.config/worklog/service-account.json`.
6. Copy the service account **email** (looks like `name@project.iam.gserviceaccount.com`).

## 2. The spreadsheet
1. Create a Google Sheet. Copy its ID from the URL
   (`https://docs.google.com/spreadsheets/d/<THIS>/edit`).
2. Add a tab named **`Log`** with header row: `Date | Hours | What I did | Project`.
3. Add a **`Report`** tab that aggregates `Log` by month with `SUMIF` totals (template
   formulas below).
4. **Share** the spreadsheet with the service account email as **Editor**.
5. Put the ID into `~/.config/worklog/config.json` → `spreadsheet_id`.
6. (RU comma decimals) File → Settings → Locale → a comma-decimal locale, so `0.5` shows as `0,5`.

### Report tab formulas (one-time)
- Grand total hours: `=SUMIF(Log!B:B,"<>",Log!B:B)` → `=SUM(Log!B2:B)`.
- Per-project total: `=SUMIF(Log!D:D, A2, Log!B:B)` (with project name in `A2`).
- Per-month total: keep a `Month` helper column in Log (`=TEXT(...)`) or use
  `=SUMPRODUCT((MONTH(...))...)`; or build a Pivot table (Insert → Pivot table) grouped by
  month/project — simplest and matches the manual report.

## 3. Install
Run `./install.sh`, then add `worklog` to PATH and register the hook (below).

## 4. Register the SessionStart hook
In `~/.claude/settings.json`:
```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [ { "type": "command", "command": "python3 /ABSOLUTE/PATH/claude-worklog-skill/hooks/session_start.py" } ] }
    ]
  }
}
```

## 5. Verify
```bash
cd /some/work/repo
worklog init "Test Project"
worklog add --project "Test Project" --hours 1 --text "setup verification" --dry-run
worklog add --project "Test Project" --hours 1 --text "setup verification"
worklog show
```
```

- [ ] **Step 4: Make scripts executable + commit**

```bash
chmod +x install.sh hooks/session_start.py
git add config.example.json install.sh docs/SETUP.md
git commit -m "feat: installer, config template, and Google Cloud setup docs"
```

---

### Task 12: Full test run + README polish

- [ ] **Step 1: Run the whole suite**

Run: `pytest -v`
Expected: PASS (all tests across the suite).

- [ ] **Step 2: Update README status section** to point at `docs/SETUP.md` and mark the
  engine/skill/hook as implemented (remove the "coming soon" line).

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: point README at setup, mark engine/skill/hook implemented"
```

---

## Self-Review

**Spec coverage:**
- Skill brain → Task 10. Engine CLI (init/add/show/projects/flush, --dry-run) → Task 8.
- Hours as estimate, 0.5 rounding, accumulation → Tasks 2, 3, skill rules in 10.
- Hybrid project resolution + `init` writing CLAUDE.md → Task 6.
- Flat `Log` + `Report` formulas → Task 11 (docs/SETUP.md); engine writes only `Log`.
- Service-account auth → Task 5 (`open_worksheet`), setup in Task 11.
- SessionStart nudge, tracked-only → Task 9.
- Offline reliability (pending.jsonl) + idempotent text dedup → Tasks 7, 3, 8.
- All commands present; `--dry-run` global. ✓

**Placeholders:** none — every code/test step is complete. Report-tab formulas are real
Sheets formulas; pivot offered as the simplest equivalent.

**Type consistency:** backend interface (`get_all_values`/`append_row`/`update_row`) is
identical in `FakeBackend`, `GspreadBackend`, and the `ListBackend` test stub. `upsert`
signature and return shape match across Tasks 3 and 8. `resolve_project` returns
`(name, source)` everywhere. ✓
```
