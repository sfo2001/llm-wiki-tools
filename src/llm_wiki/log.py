from datetime import datetime, timezone
from pathlib import Path


def append_log(wiki_dir: Path, operation: str, title: str) -> None:
    """Append one entry to wiki/log.md in chronological order."""
    log_path = wiki_dir / "log.md"
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entry = f"\n## [{date_str}] {operation} | {title}\n"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(entry)
