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
