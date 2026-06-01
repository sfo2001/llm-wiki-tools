#!/usr/bin/env bash
# run.sh — lwt wrapper for this wiki. Bootstraps a per-wiki venv from tools/*.whl.
# Usage: ./run.sh <command> [args]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV="$SCRIPT_DIR/venv"
WHEEL_DIR="$SCRIPT_DIR/tools"
MARKER="$VENV/.installed-wheel"

# Locate newest wheel
WHEEL=$(ls -t "$WHEEL_DIR"/lwt_wiki-*.whl 2>/dev/null | head -1 || true)
if [[ -z "$WHEEL" ]]; then
    echo "✗ No wheel found in $WHEEL_DIR/" >&2
    echo "  Drop a lwt_wiki-*.whl into tools/ and re-run." >&2
    exit 1
fi
WHEEL_NAME=$(basename "$WHEEL")

# Bootstrap venv if missing
if [[ ! -d "$VENV" ]]; then
    echo "→ Creating venv at $VENV"
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install --quiet --upgrade pip
fi

# Install wheel if not yet installed or wheel changed
if [[ ! -f "$MARKER" ]] || [[ "$(cat "$MARKER")" != "$WHEEL_NAME" ]]; then
    echo "→ Installing $WHEEL_NAME"
    "$VENV/bin/pip" install --quiet --force-reinstall "${WHEEL}[mkdocs]"
    echo "$WHEEL_NAME" > "$MARKER"
fi

LWT="$VENV/bin/lwt"

CMD=${1:-help}
shift 2>/dev/null || true

case "$CMD" in
  ingest)
    exec "$LWT" ingest "$@" --wiki-dir "$SCRIPT_DIR/wiki"
    ;;
  serve)
    exec "$LWT" deploy --target mkdocs --wiki-dir "$SCRIPT_DIR/wiki" "$@"
    ;;
  build)
    exec "$LWT" deploy --target mkdocs --build --wiki-dir "$SCRIPT_DIR/wiki" "$@"
    ;;
  lint)
    exec "$LWT" lint --wiki-dir "$SCRIPT_DIR/wiki" "$@"
    ;;
  search)
    exec "$LWT" search "$@" --wiki-dir "$SCRIPT_DIR/wiki"
    ;;
  log-entry)
    exec "$LWT" log-entry "$@" --wiki-dir "$SCRIPT_DIR/wiki"
    ;;
  update)
    exec "$LWT" update "$SCRIPT_DIR" "$@"
    ;;
  help|--help|-h)
    cat <<'EOF'
Usage: ./run.sh <command> [args]

Commands:
  ingest <file-or-url>      Convert source → wiki/.tmp/ then open claude
  serve                     Serve wiki at http://localhost:8000 (live reload)
  build                     Build static site → .build/site/
  lint                      Run lint checks (--all by default; pass any subset)
  search <query>            BM25 keyword search over wiki pages
  log-entry --op X --title Y  Atomically append to wiki/log.md
  update [--apply] [--force]  Refresh bundled assets (AGENTS.md, skills/, run.sh)
  update --tools <wheel>      Swap in a new lwt version

Examples:
  ./run.sh ingest raw/paper.pdf
  ./run.sh serve
  ./run.sh search "attention mechanism"
  ./run.sh update                    # dry-run; show what would change
  ./run.sh update --apply            # write canonical updates
EOF
    ;;
  *)
    exec "$LWT" "$CMD" "$@"
    ;;
esac
