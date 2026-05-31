# Security Policy

## Supported versions

`llm-wiki-tools` is in active development. Security fixes are applied to the
latest released version on the `main` branch only.

## Reporting a vulnerability

Please **do not** open a public issue for security vulnerabilities.

Instead, report privately via GitHub's
[private vulnerability reporting](https://github.com/sfo2001/llm-wiki-tools/security/advisories/new)
("Report a vulnerability" under the **Security** tab).

Please include:

- a description of the issue and its impact,
- steps to reproduce (a minimal proof of concept if possible),
- affected version / commit.

You can expect an initial acknowledgement within a few days. Once a fix is
available, the advisory will be published with credit to the reporter unless
anonymity is requested.

## Scope notes

`lwt ingest` fetches and parses untrusted sources (PDF/DOCX/PPTX/web URLs).
URL ingestion blocks internal/private network targets by default (SSRF
protection); the `--allow-internal` flag intentionally disables that guard and
should only be used with trusted hosts.
