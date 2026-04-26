import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from llm_wiki import __git_hash__, __version__
from llm_wiki.common import compute_sha, validate_ingest_url, write_tmp
from llm_wiki.ingest import confluence, docx, pdf, pptx, raw, web

EXTENSION_MAP = {
    ".pdf": pdf.convert_pdf,
    ".docx": docx.convert_docx,
    ".pptx": pptx.convert_pptx,
    ".md": raw.convert_raw,
    ".txt": raw.convert_raw,
    ".text": raw.convert_raw,
    ".rst": raw.convert_raw,
    ".org": raw.convert_raw,
}


@dataclass
class IngestResult:
    path: Path | None   # None when output="-" (stdout mode)
    lines: int
    sections: int
    backend: str
    source_sha: str


def ingest_source(
    source: str | Path,
    wiki_dir: Path,
    ingest_command: str,
    output: str | None = None,
    allow_internal: bool = False,
) -> IngestResult:
    """Dispatch source to correct handler; write to wiki/.tmp/ or stdout."""
    source_str = str(source)
    is_url = source_str.startswith("http://") or source_str.startswith("https://")

    if is_url:
        validate_ingest_url(source_str, allow_internal=allow_internal)
        if "/rest/api/content/" in source_str:
            import os
            token = os.environ.get("CONFLUENCE_TOKEN", "")
            backend_name, md_body = confluence.convert_confluence(source_str, token)
        else:
            backend_name, md_body = web.convert_web(source_str)
        # synthetic path for URL sources (write URL bytes so compute_sha works)
        safe = re.sub(r"[^\w]", "_", source_str)[:60]
        tmp_dir = wiki_dir / ".tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        source_path = tmp_dir / f"{safe}.url"
        source_path.write_bytes(source_str.encode())
    else:
        source_path = Path(source)
        ext = source_path.suffix.lower()
        handler = EXTENSION_MAP.get(ext)
        if handler is None:
            raise ValueError(
                f"Unsupported source format: {ext!r}. "
                f"Supported: {sorted(EXTENSION_MAP)}"
            )
        backend_name, md_body = handler(source_path)

    if output == "-":
        source_sha = compute_sha(source_path)
        meta = {
            "source": str(source_path),
            "source-sha": source_sha,
            "ingest-command": ingest_command,
            "ingest-backend": backend_name,
            "lwt-version": __version__,
            "lwt-git-hash": __git_hash__,
            "ingested-at": datetime.now(timezone.utc).isoformat(),
        }
        fm = yaml.dump(meta, default_flow_style=False, allow_unicode=True)
        sys.stdout.write(f"---\n{fm}---\n\n{md_body}\n")
        lines = len(md_body.splitlines())
        sections = len(re.findall(r"^#{1,3} ", md_body, re.MULTILINE))
        return IngestResult(path=None, lines=lines, sections=sections,
                            backend=backend_name, source_sha=source_sha)

    out_path, summary = write_tmp(
        wiki_dir=wiki_dir,
        source_path=source_path,
        backend_name=backend_name,
        markdown_body=md_body,
        ingest_command=ingest_command,
    )
    return IngestResult(
        path=out_path,
        lines=summary["lines"],
        sections=summary["sections"],
        backend=summary["backend"],
        source_sha=summary["source_sha"],
    )
