# Contributing to llm-wiki-tools

Thanks for your interest in contributing! This document covers the basics.

## Development setup

Requires **Python 3.10+**.

```bash
git clone https://github.com/sfo2001/llm-wiki-tools.git
cd llm-wiki-tools
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"        # add ",mkdocs" to work on the MkDocs backend
```

## Running tests

```bash
pytest            # full suite
pytest -q         # quiet
```

CI runs the suite on Python 3.10, 3.11, 3.12, and 3.13. Please make sure tests pass
locally before opening a pull request, and add tests for new behavior.

## Pull requests

1. Fork the repo and create a feature branch off `main`.
2. Keep changes focused; one logical change per PR.
3. Follow the existing code style and conventions.
4. Use clear commit messages (Conventional Commits style is appreciated,
   e.g. `fix(ingest): handle empty PDF pages`).
5. Update relevant docs in `docs/` and `docs/roadmap.md` when behavior changes.
6. Open the PR with a description of *what* changed and *why*.

## Architecture & conventions

- [`docs/architecture.md`](docs/architecture.md) — component layout and data flow.
- [`docs/adr/`](docs/adr/) — architecture decision records; add one for
  non-obvious choices.
- [`AGENTS.md`](AGENTS.md) — the agent/wiki contract that governs `wiki/` layout.

## Reporting bugs

Open an issue with reproduction steps, expected vs. actual behavior, your OS,
and Python version. For security issues, see [SECURITY.md](SECURITY.md) instead.

## License

By contributing, you agree that your contributions will be licensed under the
[MIT License](LICENSE).
