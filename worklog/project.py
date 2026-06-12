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
    lj.write_text(
        json.dumps({"project": name}, ensure_ascii=False, indent=2), encoding="utf-8"
    )

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
