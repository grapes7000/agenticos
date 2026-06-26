from pathlib import Path
from datetime import datetime
import json
import os
import sqlite3

try:
    from agents.note_policy import frontmatter, latest_note_name
except ModuleNotFoundError:
    from note_policy import frontmatter, latest_note_name

VAULT = Path(os.getenv('OBSIDIAN_VAULT', str(Path.home() / 'vault'))).expanduser()
OUT_DIR = VAULT / 'Agentic OS' / 'Handoffs'
OUT_DIR.mkdir(parents=True, exist_ok=True)
DB = Path('data/db/agent_os.sqlite')

def newest(folder):
    d = VAULT / 'Agentic OS' / folder
    if not d.exists():
        return None
    files = sorted(d.glob('*.md'), key=lambda p: p.stat().st_mtime)
    return str(files[-1]) if files else None

payload = {
    'created_at': datetime.now().isoformat(timespec='seconds'),
    'agent': 'layer3-handoff-writer',
    'status': 'complete',
    'summary': 'Layer 3 run completed. Review health, evaluation, memory index, and generated reports.',
    'latest': {
        'health': newest('Health'),
        'evaluation': newest('Evaluations'),
        'operator_report': newest('Operator Reports'),
        'file_plan': newest('File Plans'),
        'daily_briefing': newest('Daily Briefings'),
        'search_results': newest('Search Results'),
    },
    'next_agent': 'hermes-operator',
    'guardrails': [
        'Do not auto-delete or auto-move files.',
        'Do not access wallets, seed phrases, bank files, or browser cookies.',
        'Use OpenClaw only through the sandbox context pack until explicitly expanded.'
    ]
}

stamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
json_out = Path('data/handoffs') / f'{stamp}_handoff.json'
json_out.parent.mkdir(parents=True, exist_ok=True)
json_out.write_text(json.dumps(payload, indent=2), encoding='utf-8')

md_out = OUT_DIR / latest_note_name('AI-LEARN', 'Handoff')
lines = [
    *frontmatter('AI-LEARN: AgenticOS Handoff', 'ai_future', ['agentic-os', 'handoff', 'ai-learn'], 'Latest Layer 3 handoff for future AI operators.'),
    '',
    f'# AI-LEARN: AgenticOS Handoff - {stamp}',
    '',
    f'- Agent: `{payload["agent"]}`',
    f'- Status: `{payload["status"]}`',
    f'- Next agent: `{payload["next_agent"]}`',
    '',
    '## Summary',
    '',
    payload['summary'],
    '',
    '## Latest Artifacts',
    '',
]
for k, v in payload['latest'].items():
    lines.append(f'- **{k}:** `{v or "missing"}`')
lines.extend(['', '## Guardrails', ''])
lines.extend([f'- {g}' for g in payload['guardrails']])
md_out.write_text('\n'.join(lines), encoding='utf-8')

DB.parent.mkdir(parents=True, exist_ok=True)
with sqlite3.connect(DB) as con:
    con.execute('INSERT INTO handoffs(agent, status, summary, next_agent, payload_json) VALUES (?, ?, ?, ?, ?)',
                (payload['agent'], payload['status'], payload['summary'], payload['next_agent'], json.dumps(payload)))

print(f'Wrote handoff: {md_out}')
print(f'Wrote handoff JSON: {json_out}')
