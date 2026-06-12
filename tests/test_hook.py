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
    (tmp_path / "CLAUDE.md").write_text(
        'worklog-project: "content.fans"\n', encoding="utf-8"
    )
    res = _run(tmp_path)
    assert "worklog" in res.stdout.lower()
    assert "content.fans" in res.stdout
