#!/usr/bin/env bash
# run.sh — lwt wrapper for this wiki. Usage: ./run.sh <command> [args]
set -e

CMD=${1:-help}
shift 2>/dev/null || true

case "$CMD" in
  ingest)
    lwt ingest "$@" --wiki-dir wiki
    ;;
  serve)
    lwt deploy --target mkdocs --wiki-dir wiki "$@"
    ;;
  build)
    lwt deploy --target mkdocs --build --wiki-dir wiki "$@"
    ;;
  lint)
    lwt lint --structural --wiki-dir wiki
    ;;
  search)
    lwt search "$@" --wiki-dir wiki
    ;;
  help|--help|-h|*)
    echo "Usage: ./run.sh <command> [args]"
    echo ""
    echo "Commands:"
    echo "  ingest <file-or-url>   Convert source → wiki/.tmp/ then open claude"
    echo "  serve                  Serve wiki at http://localhost:8000 (live reload)"
    echo "  build                  Build static site → .build/site/"
    echo "  lint                   Check for broken links and orphaned pages"
    echo "  search <query>         BM25 keyword search over wiki pages"
    echo ""
    echo "Examples:"
    echo "  ./run.sh ingest raw/paper.pdf"
    echo "  ./run.sh ingest https://example.com/article"
    echo "  ./run.sh serve"
    echo "  ./run.sh search \"attention mechanism\""
    ;;
esac
