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
