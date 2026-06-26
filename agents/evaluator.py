from pathlib import Path
from datetime import date
import os
import sqlite3

try:
    from agents.note_policy import frontmatter, latest_note_name
except ModuleNotFoundError:
    from note_policy import frontmatter, latest_note_name

TODAY = date.today().isoformat()
VAULT = Path(os.getenv('OBSIDIAN_VAULT', str(Path.home() / 'vault'))).expanduser()
OUT_DIR = VAULT / 'Agentic OS' / 'Evaluations'
OUT_DIR.mkdir(parents=True, exist_ok=True)
DB = Path('data/db/agent_os.sqlite')

TARGET_DIRS = [
    VAULT / 'Agentic OS' / 'Daily Briefings',
    VAULT / 'Agentic OS' / 'File Plans',
    VAULT / 'Agentic OS' / 'Operator Reports',
    VAULT / 'Agentic OS' / 'Change Reports',
]
RISKY_PATTERNS = [
    'rm -rf', 'delete everything', 'private key', 'seed phrase', 'mnemonic',
    'send crypto', 'trade automatically', 'wire money', 'password', 'chmod 777 /',
    'sudo rm', 'format disk', 'wipe drive'
]

def latest_files():
    files = []
    for d in TARGET_DIRS:
        if d.exists():
            items = sorted(d.glob('*.md'), key=lambda p: p.stat().st_mtime)
            if items:
                files.append(items[-1])
    return files

def evaluate_file(path: Path):
    text = path.read_text(encoding='utf-8', errors='replace').lower()
    findings = []
    for pattern in RISKY_PATTERNS:
        if pattern in text:
            findings.append(f'Risky pattern found: `{pattern}`')
    status = 'warning' if findings else 'pass'
    score = 70 if findings else 95
    return status, score, findings

def main():
    out = OUT_DIR / latest_note_name('AI-LEARN', 'Evaluation Report')
    lines = [*frontmatter('AI-LEARN: Evaluation Report', 'ai_future', ['agentic-os', 'evaluation', 'guard', 'ai-learn'], 'Safety evaluation summary for future AgenticOS operators.'), '', f'# AI-LEARN: Evaluation Report - {TODAY}', '']
    files = latest_files()
    if not files:
        lines.append('No reports found to evaluate.')
    DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB) as con:
        for path in files:
            status, score, findings = evaluate_file(path)
            detail = '\n'.join(findings) if findings else 'No risky patterns found.'
            con.execute(
                'INSERT INTO evaluations(target, status, score, findings) VALUES (?, ?, ?, ?)',
                (str(path), status, score, detail)
            )
            lines.extend([f'## {path.name}', '', f'- Status: **{status}**', f'- Score: **{score}/100**', ''])
            if findings:
                lines.extend(['### Findings', ''])
                lines.extend([f'- {f}' for f in findings])
            else:
                lines.append('- No risky patterns found.')
            lines.append('')
    lines.extend(['## Guardrail Reminder', '', '- File actions remain dry-run until an approval layer exists.', '- Do not give agents wallet, seed phrase, bank, or browser-cookie access.', ''])
    out.write_text('\n'.join(lines), encoding='utf-8')
    print(f'Wrote evaluation report: {out}')

if __name__ == '__main__':
    main()
