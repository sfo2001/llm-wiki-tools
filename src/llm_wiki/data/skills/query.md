# Query Workflow Skill

## When to use

When a user asks a question against the wiki.

## Decision tree by wiki size

- **< 50 pages:** Read wiki/index.md, identify candidates, use Read tool directly.
- **50–200 pages:** Run `lwt search "<key terms>"` first, then Read top results.
- **> 200 pages:** Run `lwt search "<key terms>"` + `Grep` for exact matches.

## Steps

1. Read `wiki/index.md` — scan for relevant pages by title and summary
2. If index is large or ambiguous: `lwt search "<key terms>" --wiki-dir wiki`
3. Read top candidate pages with Read/Grep tools
4. Synthesize answer with `[[wiki-page]]` citations
5. Ask user: "Worth filing this as a wiki page?"

## When to file answers back

File if the answer:
- Synthesizes across 3+ wiki pages
- Makes a comparison or analysis the user will want again
- Reveals a connection not explicit in any single page
- Answers a question that will recur

**Do NOT file:** one-sentence lookups, navigation answers, ephemeral status questions.

## Filing a query answer

1. Write `wiki/queries/<slug>.md` using `templates/query-answer.md`
2. Set `query:` frontmatter to the original question
3. Update `wiki/index.md` — add one-line entry under Queries
4. Append to `wiki/log.md`: `## [YYYY-MM-DD] query | <question summary>`
