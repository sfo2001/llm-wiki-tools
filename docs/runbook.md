---
project: llm-wiki-tools
last_updated: 2026-04-19
---

# llm-wiki-tools — Runbook

`lwt` is a one-shot CLI, not a long-running service. "Start" means
install and invoke; "stop" only applies to the `lwt deploy` subcommand
which runs a foreground server.

## Install

```bash
cd /path/to/llm-wiki-tools
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
lwt --version
```

## Start (deploy target)

```bash
cd <your-wiki-data-repo>
lwt deploy --target local               # mkdocs/grip/http.server on :8080
lwt deploy --target docker --mode volume  # nginx:alpine, wiki/ mounted ro, :8443
lwt deploy --target confluence          # dry-run list of pages
lwt deploy --target confluence --no-dry-run   # live push (needs env vars)
```

## Stop

`local` and `docker --mode volume` run in the foreground — `Ctrl-C`
the process. For the docker backend the `subprocess.run(["docker", "run", "-d", ...])`
returns a container id; stop it with:

```bash
docker ps --filter ancestor=nginx:alpine
docker stop <container-id>
```

The CLI subcommands `ingest` / `search` / `lint` / `init` exit when
done; there is nothing to stop.

## Check it's alive

```bash
# CLI reachable:
lwt --version

# Local deploy:
curl -sf http://localhost:8080/ >/dev/null && echo OK

# Docker deploy:
curl -sf http://localhost:8443/ >/dev/null && echo OK

# Confluence reachable (when configured):
curl -sf -H "Authorization: Bearer $CONFLUENCE_TOKEN" \
  "$CONFLUENCE_URL/rest/api/content?spaceKey=$CONFLUENCE_SPACE&limit=1" | head -c 120
```

## Common tasks

### Update the config

Edit `pyproject.toml` for tool-side config (deps, entry point). Data
repos (created via `lwt init <path>`) carry their own `AGENTS.md`,
`CLAUDE.md`, and `.lwt.env.example` — edit those in the data repo,
not here. Reload is implicit: `lwt` reads everything fresh per
invocation.

### Restart after a NAS reboot

`lwt` itself has no persistent state to restart. For docker deploys:

```bash
docker start <container-id>
# or redeploy fresh:
cd <your-wiki-data-repo>
lwt deploy --target docker --mode volume
```

### Backup / restore

Nothing `lwt` writes needs explicit backup — it is a pure function of
the data repo.

- **Data repo** (`wiki/`, `raw/`, `templates/`, `AGENTS.md`): commit to
  git; that IS the backup.
- **Search cache** (`.search-index.json`): regenerable via
  `lwt search <anything> --reindex`. Safe to delete.
- **Temp ingests** (`wiki/.tmp/`): regenerable via `lwt ingest`. Safe
  to delete; gitignored.
- **Lint report** (`wiki/lint-report.md`): regenerable via
  `lwt lint --structural`.

## Things that have broken before

Append entries as they happen:

### 2026-04-19 — Docker image mode silently failed without Dockerfile

**Symptom:** `lwt deploy --target docker --mode image` returned non-zero
with no clear error.

**Fix:** `DockerBackend._image_command` now raises `FileNotFoundError`
with a remediation hint when `wiki_dir/Dockerfile` is absent
(commit `50eac8a`).

**Root cause:** `docker build` was invoked without checking for the
Dockerfile, producing a terse build error.
