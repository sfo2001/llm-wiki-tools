from datetime import datetime, timezone
from pathlib import Path


def append_log(
    wiki_dir: Path, operation: str, title: str, body: str | None = None,
) -> None:
    """Append one entry to wiki/log.md. Never modifies existing content.

    Always writes at the end of the file. Body is appended below the header
    with a blank-line separator. Output ends with a single trailing newline.
    """
    log_path = wiki_dir / "log.md"
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    header = f"## [{date_str}] {operation} | {title}"

    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    if existing and not existing.endswith("\n"):
        existing += "\n"

    block = f"\n{header}\n"
    if body:
        block += "\n" + body.rstrip("\n") + "\n"

    log_path.write_text(existing + block, encoding="utf-8")
