#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DB = Path(os.getenv('AGENTOS_MEMORY_DB', str(ROOT / 'data' / 'db' / 'agent_os.sqlite'))).expanduser()
CHAT_DB = Path(os.getenv('CHATGPT_MEMORY_DB', str(ROOT / 'chatgpt-memory' / 'data' / 'memory.sqlite3'))).expanduser()
VAULT = Path(os.getenv('OBSIDIAN_VAULT', str(Path.home() / 'vault'))).expanduser()
OUT_DIR = VAULT / 'Agentic OS' / 'Search Results'
EMBED_MODEL = os.getenv('AGENTOS_EMBED_MODEL', 'nomic-embed-text')
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434').rstrip('/')


def ollama_base(host: str) -> str:
    host = host.strip().rstrip('/')
    if not host.startswith(('http://', 'https://')):
        host = 'http://' + host
    return host


def _post_json(url: str, payload: dict[str, Any]):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode('utf-8'))


def embed(text: str):
    base = ollama_base(OLLAMA_HOST)
    try:
        data = _post_json(f'{base}/api/embeddings', {'model': EMBED_MODEL, 'prompt': text[:8000]})
        if data.get('embedding'):
            return data['embedding']
    except urllib.error.HTTPError as exc:
        if exc.code not in {404, 405}:
            raise
    data = _post_json(f'{base}/api/embed', {'model': EMBED_MODEL, 'input': text[:8000]})
    embeddings = data.get('embeddings') or []
    return embeddings[0] if embeddings and isinstance(embeddings[0], list) else None


def cosine(a, b):
    if not a or not b or len(a) != len(b):
        return -1
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else -1


def keyword_score(query, text):
    terms = [t.lower() for t in query.split() if len(t) > 2]
    lower = text.lower()
    return sum(lower.count(t) for t in terms)


def _safe_json_embedding(value: str | None):
    if not value:
        return None
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, list) else None


def load_obsidian():
    if not DB.exists():
        return []
    try:
        with sqlite3.connect(DB) as con:
            rows = con.execute(
                'SELECT source_path, title, chunk_text, embedding_json FROM memory_chunks'
            ).fetchall()
    except sqlite3.Error:
        return []
    return [
        {
            'source_type': 'obsidian',
            'source': source_path,
            'title': title or Path(source_path).stem,
            'text': chunk_text,
            'embedding': _safe_json_embedding(embedding_json),
            'metadata': {},
        }
        for source_path, title, chunk_text, embedding_json in rows
    ]


def load_chatgpt():
    if not CHAT_DB.exists():
        return []
    try:
        with sqlite3.connect(CHAT_DB) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute(
                '''
                SELECT cc.chunk_text,cc.embedding_json,cc.start_message,cc.end_message,
                       c.conversation_id,c.title,c.created_at,c.source_file
                FROM chat_chunks cc JOIN conversations c USING(conversation_id)
                '''
            ).fetchall()
    except sqlite3.Error:
        return []
    results = []
    for row in rows:
        cid = row['conversation_id']
        results.append(
            {
                'source_type': 'chatgpt',
                'source': f'chatgpt://conversation/{cid}#messages={row["start_message"]}-{row["end_message"]}',
                'title': row['title'] or cid,
                'text': row['chunk_text'],
                'embedding': _safe_json_embedding(row['embedding_json']),
                'metadata': {
                    'conversation_id': cid,
                    'date': row['created_at'],
                    'source_file': row['source_file'],
                    'message_range': f'{row["start_message"]}-{row["end_message"]}',
                },
            }
        )
    return results


def load_assets():
    if not CHAT_DB.exists():
        return []
    try:
        with sqlite3.connect(CHAT_DB) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute(
                '''
                SELECT ac.chunk_text,ac.embedding_json,ac.content_kind,a.asset_id,a.source_path,
                       a.recovered_path,a.detected_mime,a.recovered_ext,
                       (SELECT original_name FROM asset_references r
                        WHERE r.asset_id=a.asset_id AND original_name IS NOT NULL
                        ORDER BY rowid LIMIT 1) AS original_name
                FROM asset_chunks ac JOIN assets a USING(asset_id)
                '''
            ).fetchall()
    except sqlite3.Error:
        return []
    results = []
    for row in rows:
        source = row['recovered_path'] or row['source_path']
        title = row['original_name'] or f'file_{row["asset_id"]}{row["recovered_ext"]}'
        results.append(
            {
                'source_type': 'asset',
                'source': source,
                'title': title,
                'text': row['chunk_text'],
                'embedding': _safe_json_embedding(row['embedding_json']),
                'metadata': {
                    'asset_id': row['asset_id'],
                    'mime': row['detected_mime'],
                    'content_kind': row['content_kind'],
                    'raw_source': row['source_path'],
                },
            }
        )
    return results


def search(query: str, limit: int = 8, include: set[str] | None = None):
    include = include or {'obsidian', 'chatgpt', 'asset'}
    rows = []
    if 'obsidian' in include:
        rows.extend(load_obsidian())
    if 'chatgpt' in include:
        rows.extend(load_chatgpt())
    if 'asset' in include:
        rows.extend(load_assets())

    qemb = None
    try:
        qemb = embed(query)
    except Exception:
        pass

    scored = []
    for row in rows:
        score = float(keyword_score(query, row['text']))
        if qemb and row['embedding']:
            similarity = cosine(qemb, row['embedding'])
            if similarity >= 0:
                score += 10.0 * similarity
        if score > 0:
            scored.append({**row, 'score': score})
    scored.sort(key=lambda item: item['score'], reverse=True)
    return scored[:limit]


def write_results(query: str, results: list[dict[str, Any]]) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    safe_query = query[:40].replace('/', '-')
    out = OUT_DIR / f'{stamp} Search - {safe_query}.md'
    lines = [f'# Memory Search: {query}', '', f'Results: {len(results)}', '']
    for index, result in enumerate(results, 1):
        excerpt = result['text'].replace('\n', ' ')[:900]
        lines.extend(
            [
                f'## {index}. {result["title"]}',
                '',
                f'- Type: `{result["source_type"]}`',
                f'- Source: `{result["source"]}`',
                f'- Score: `{result["score"]:.3f}`',
            ]
        )
        for key, value in result['metadata'].items():
            if value not in (None, ''):
                lines.append(f'- {key.replace("_", " ").title()}: `{value}`')
        lines.extend(['', excerpt, ''])
    out.write_text('\n'.join(lines), encoding='utf-8')
    return out


def parse_args():
    parser = argparse.ArgumentParser(description='Hybrid semantic search across AgenticOS memory.')
    parser.add_argument('query', nargs='+')
    parser.add_argument('--limit', type=int, default=8)
    parser.add_argument('--obsidian', action='store_true', help='Search only/select Obsidian memory')
    parser.add_argument('--chatgpt', action='store_true', help='Search only/select ChatGPT conversation chunks')
    parser.add_argument('--assets', action='store_true', help='Search only/select recovered ChatGPT assets')
    parser.add_argument('--no-write', action='store_true', help='Do not write a Markdown result file')
    return parser.parse_args()


def main():
    args = parse_args()
    query = ' '.join(args.query)
    selected = set()
    if args.obsidian:
        selected.add('obsidian')
    if args.chatgpt:
        selected.add('chatgpt')
    if args.assets:
        selected.add('asset')
    results = search(query, limit=args.limit, include=selected or None)

    if not args.no_write:
        out = write_results(query, results)
        print(f'Wrote memory search results: {out}')
    for index, result in enumerate(results, 1):
        print(
            f'{index}. [{result["source_type"]}] {result["title"]} :: '
            f'{result["source"]} :: {result["score"]:.3f}'
        )


if __name__ == '__main__':
    main()
