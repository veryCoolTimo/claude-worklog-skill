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
