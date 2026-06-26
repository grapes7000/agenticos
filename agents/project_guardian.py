from pathlib import Path
from datetime import date
import os

TODAY = date.today().isoformat()
VAULT = Path(os.getenv('OBSIDIAN_VAULT', str(Path.home() / 'vault'))).expanduser()
OUT_DIR = VAULT / 'Agentic OS' / 'Project Guardian'
OUT_DIR.mkdir(parents=True, exist_ok=True)

KEYWORDS = ['TODO', 'NEXT', 'FIXME', 'bug', 'broken', 'agentos', 'hermes', 'qwen', 'openclaw']
MAX_FILES = 80

matches = []
for p in VAULT.rglob('*.md'):
    if any(part in {'.obsidian', '.git'} for part in p.parts):
        continue
    try:
        text = p.read_text(encoding='utf-8', errors='replace')
    except Exception:
        continue
    lower = text.lower()
    if any(k.lower() in lower for k in KEYWORDS):
        lines = []
        for line in text.splitlines():
            if any(k.lower() in line.lower() for k in KEYWORDS):
                lines.append(line.strip()[:240])
        matches.append((p, lines[:8]))
    if len(matches) >= MAX_FILES:
        break

out = OUT_DIR / f'{TODAY} Project Guardian.md'
lines = ['---', 'tags: [agentic-os, project-guardian]', f'created: {TODAY}', '---', '', f'# Project Guardian - {TODAY}', '', '## Potential Project Signals', '']
if not matches:
    lines.append('No project signals found.')
else:
    for p, snippets in matches:
        lines.extend([f'## {p.stem}', '', f'- File: `{p}`', ''])
        for s in snippets:
            lines.append(f'- {s}')
        lines.append('')
lines.extend(['## Suggested Next Actions', '', '- Pick one active project to move forward today.', '- Keep AgenticOS infrastructure stable before adding risky desktop control.', ''])
out.write_text('\n'.join(lines), encoding='utf-8')
print(f'Wrote project guardian report: {out}')
