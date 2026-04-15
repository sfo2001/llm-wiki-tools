from llm_wiki.lint.structural import Finding


def format_report(findings: list[Finding]) -> str:
    if not findings:
        return "No issues found.\n"
    lines = [
        f"{f.path}:{f.line}: [{f.issue_type}] {f.message}"
        for f in sorted(findings, key=lambda x: (str(x.path), x.line))
    ]
    return "\n".join(lines) + "\n"
