from pathlib import Path
import json
import math
import os
import sqlite3
import sys
import urllib.request

DB = Path('data/db/agent_os.sqlite')
VAULT = Path(os.getenv('OBSIDIAN_VAULT', str(Path.home() / 'vault'))).expanduser()
OUT_DIR = VAULT / 'Agentic OS' / 'Search Results'
OUT_DIR.mkdir(parents=True, exist_ok=True)
EMBED_MODEL = os.getenv('AGENTOS_EMBED_MODEL', 'nomic-embed-text')
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434').rstrip('/')

def embed(text: str):
    payload = {'model': EMBED_MODEL, 'prompt': text[:4000]}
    req = urllib.request.Request(
        f'{OLLAMA_HOST}/api/embeddings',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    return data.get('embedding')

def cosine(a, b):
    if not a or not b or len(a) != len(b):
        return -1
    dot = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(y*y for y in b))
    return dot / (na*nb) if na and nb else -1

def keyword_score(query, text):
    terms = [t.lower() for t in query.split() if len(t) > 2]
    lower = text.lower()
    return sum(lower.count(t) for t in terms)

def search(query, limit=8):
    with sqlite3.connect(DB) as con:
        rows = con.execute('SELECT source_path, title, chunk_text, embedding_json FROM memory_chunks').fetchall()
    qemb = None
    try:
        qemb = embed(query)
    except Exception:
        pass
    scored = []
    for source_path, title, chunk_text, embedding_json in rows:
        score = keyword_score(query, chunk_text)
        if qemb and embedding_json:
            try:
                score += 10 * cosine(qemb, json.loads(embedding_json))
            except Exception:
                pass
        if score > 0:
            scored.append((score, source_path, title, chunk_text))
    scored.sort(reverse=True, key=lambda x: x[0])
    return scored[:limit]

def main():
    if len(sys.argv) < 2:
        raise SystemExit('Usage: python3 tools/search_memory.py "query"')
    query = ' '.join(sys.argv[1:])
    results = search(query)
    from datetime import datetime
    stamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    out = OUT_DIR / f'{stamp} Search - {query[:40].replace("/", "-")}.md'
    lines = [f'# Memory Search: {query}', '', f'Results: {len(results)}', '']
    for i, (score, source, title, text) in enumerate(results, 1):
        excerpt = text.replace('\n', ' ')[:700]
        lines.extend([f'## {i}. {title or Path(source).stem}', '', f'- Source: `{source}`', f'- Score: `{score:.3f}`', '', excerpt, ''])
    out.write_text('\n'.join(lines), encoding='utf-8')
    print(f'Wrote memory search results: {out}')
    for i, (score, source, title, text) in enumerate(results[:5], 1):
        print(f'{i}. {title or Path(source).stem} :: {source} :: {score:.3f}')

if __name__ == '__main__':
    main()
