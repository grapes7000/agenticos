from pathlib import Path
from datetime import date
import os
import shutil
import sqlite3
import subprocess

try:
    from agents.note_policy import frontmatter, latest_note_name
except ModuleNotFoundError:
    from note_policy import frontmatter, latest_note_name

TODAY = date.today().isoformat()
VAULT = Path(os.getenv('OBSIDIAN_VAULT', str(Path.home() / 'vault'))).expanduser()
OUT_DIR = VAULT / 'Agentic OS' / 'Health'
OUT_DIR.mkdir(parents=True, exist_ok=True)
DB = Path('data/db/agent_os.sqlite')

def run(cmd):
    try:
        r = subprocess.run(cmd, text=True, capture_output=True, timeout=20)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except Exception as e:
        return 1, '', str(e)

def latest_count(rel):
    d = VAULT / 'Agentic OS' / rel
    if not d.exists():
        return 0, None
    files = sorted(d.glob('*.md'), key=lambda p: p.stat().st_mtime)
    return len(files), files[-1] if files else None

def main():
    lines = [*frontmatter('READ-ME: AgenticOS Health', 'human', ['agentic-os', 'health', 'read-me'], 'Readable health snapshot for Lakota.'), '', f'# READ-ME: AgenticOS Health - {TODAY}', '']
    checks = []
    checks.append(('AgenticOS folder', Path.home() / 'AgenticOS', (Path.home() / 'AgenticOS').exists()))
    checks.append(('Obsidian vault', VAULT, VAULT.exists()))
    checks.append(('SQLite database', DB, DB.exists()))

    lines.extend(['## Core Files', ''])
    for name, path, ok in checks:
        lines.append(f'- {name}: {"✅" if ok else "❌"} `{path}`')
    lines.append('')

    lines.extend(['## Tools', ''])
    for tool in ['ollama', 'qwen', 'hermes', 'openclaw', 'aider']:
        found = shutil.which(tool)
        lines.append(f'- `{tool}`: {"✅ " + found if found else "not found"}')
    lines.append('')

    if shutil.which('ollama'):
        code, out, err = run(['ollama', 'list'])
        lines.extend(['## Ollama Models', '', '```', out or err, '```', ''])

    if shutil.which('hermes'):
        code, out, err = run(['hermes', 'cron', 'list'])
        lines.extend(['## Hermes Cron', '', '```', out or err, '```', ''])

    lines.extend(['## Generated Notes', ''])
    for rel in ['File Plans', 'Daily Briefings', 'Operator Reports', 'Evaluations', 'Handoffs', 'Memory', 'Search Results']:
        count, latest = latest_count(rel)
        lines.append(f'- {rel}: **{count}** notes' + (f' latest `{latest.name}`' if latest else ''))
    lines.append('')

    if DB.exists():
        try:
            with sqlite3.connect(DB) as con:
                for table in ['files', 'lessons', 'memory_chunks', 'handoffs', 'evaluations', 'agent_runs']:
                    try:
                        c = con.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
                        lines.append(f'- DB `{table}` rows: **{c}**')
                    except Exception as e:
                        lines.append(f'- DB `{table}` check failed: `{e}`')
        except Exception as e:
            lines.append(f'- DB open failed: `{e}`')
    lines.append('')

    out = OUT_DIR / latest_note_name('READ-ME', 'Health Report')
    out.write_text('\n'.join(lines), encoding='utf-8')
    print(f'Wrote health report: {out}')

if __name__ == '__main__':
    main()
