from datetime import datetime

NOTE_POLICY = """Generated Markdown must be either AI-LEARN (for future AI/agents) or READ-ME (for Lakota). Low-signal raw/repetitive data belongs in SQLite/JSON/TXT, not timestamped Obsidian Markdown."""


def frontmatter(title: str, audience: str, tags=None, purpose: str = ""):
    tags = tags or ["agentic-os"]
    lines = [
        "---",
        f'title: "{title}"',
        f"audience: {audience}",
        "generated_by: AgenticOS",
        f"created: {datetime.now().isoformat(timespec='seconds')}",
        "tags:",
    ]
    for tag in tags:
        lines.append(f"  - {tag}")
    if purpose:
        lines.append(f'purpose: "{purpose}"')
    lines.append("---")
    return lines


def latest_note_name(kind: str, subject: str) -> str:
    if kind not in {"AI-LEARN", "READ-ME"}:
        raise ValueError("kind must be AI-LEARN or READ-ME")
    return f"latest {kind} {subject}.md"
