"""lwt update — refresh bundled assets in an existing wiki data repo.

Phase 1: hardcoded file taxonomy (canonical vs customisable), no manifest.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

_DATA_DIR = Path(__file__).parent / "data"

CANONICAL_FILES: tuple[str, ...] = (
    "AGENTS.md",
    "skills/ingest.md",
    "skills/query.md",
    "skills/lint.md",
    "skills/deploy.md",
    "run.sh",
    "run.ps1",
)

CUSTOMISABLE_FILES: tuple[str, ...] = (
    "CLAUDE.md",
    "README.md",
    "templates/default.md",
    "templates/entity.md",
    "templates/concept.md",
    "templates/source-summary.md",
    "templates/query-answer.md",
    ".gitignore",
    ".lwt.env.example",
)

_BUNDLED_FILES: tuple[str, ...] = CANONICAL_FILES + CUSTOMISABLE_FILES

_BUNDLE_NAME_OVERRIDES: dict[str, str] = {
    ".gitignore": ".gitignore.template",
    "README.md": "README.md.template",
}


def _bundle_path(rel: str) -> Path:
    return _DATA_DIR / _BUNDLE_NAME_OVERRIDES.get(rel, rel)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class FileStatus:
    rel_path: str
    class_: Literal["canonical", "customisable"]
    state: Literal["identical", "differs", "missing"]
    bundle_bytes: bytes
    deployed_bytes: bytes | None


def _classify(rel: str) -> Literal["canonical", "customisable"]:
    return "canonical" if rel in CANONICAL_FILES else "customisable"


def _read_bundle(rel: str, name: str = "my-wiki") -> bytes:
    raw = _bundle_path(rel).read_bytes()
    if rel == "README.md":
        return raw.replace(b"__NAME__", name.encode())
    return raw


def detect_name(target_dir: Path) -> str:
    """Recover the wiki name from the deployed README.md line 1.

    Falls back to 'my-wiki' if the README is missing or doesn't match the template.
    """
    readme = target_dir / "README.md"
    if not readme.exists():
        return "my-wiki"
    first_line = readme.read_text(encoding="utf-8").splitlines()[:1]
    if not first_line:
        return "my-wiki"
    line = first_line[0]
    if line.startswith("# ") and line.endswith(" Wiki"):
        return line[2:-5]
    return "my-wiki"


def compute_status(target_dir: Path, name: str = "my-wiki") -> list[FileStatus]:
    """Inspect every bundled file under target_dir; return per-file status."""
    statuses: list[FileStatus] = []
    for rel in _BUNDLED_FILES:
        bundle_bytes = _read_bundle(rel, name=name)
        dep_path = target_dir / rel
        if not dep_path.exists():
            statuses.append(FileStatus(
                rel_path=rel, class_=_classify(rel),
                state="missing", bundle_bytes=bundle_bytes,
                deployed_bytes=None,
            ))
            continue
        deployed_bytes = dep_path.read_bytes()
        state = "identical" if _sha(deployed_bytes) == _sha(bundle_bytes) else "differs"
        statuses.append(FileStatus(
            rel_path=rel, class_=_classify(rel),
            state=state, bundle_bytes=bundle_bytes,
            deployed_bytes=deployed_bytes,
        ))
    return statuses


def apply_update(target_dir: Path, *, force: bool = False, name: str = "my-wiki") -> list[FileStatus]:
    """Apply bundled-file updates to target_dir. Returns the list of files actually written."""
    written: list[FileStatus] = []
    for s in compute_status(target_dir, name=name):
        if s.state == "identical":
            continue
        if s.class_ == "customisable" and not force:
            continue
        out = target_dir / s.rel_path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(s.bundle_bytes)
        if s.rel_path == "run.sh":
            os.chmod(out, 0o755)
        written.append(s)
    return written
