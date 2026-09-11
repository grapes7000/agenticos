from pathlib import Path
import hashlib
import json
import os
import sqlite3
import urllib.request

DB = Path('data/db/agent_os.sqlite')
VAULT = Path(os.getenv('OBSIDIAN_VAULT', str(Path.home() / 'vault'))).expanduser()
EMBED_MODEL = os.getenv('AGENTOS_EMBED_MODEL', 'nomic-embed-text')
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434').rstrip('/')
MAX_FILE_CHARS = int(os.getenv('AGENTOS_MAX_FILE_CHARS', '60000'))
CHUNK_SIZE = int(os.getenv('AGENTOS_CHUNK_SIZE', '2400'))
CHUNK_OVERLAP = int(os.getenv('AGENTOS_CHUNK_OVERLAP', '300'))

SKIP_DIR_PARTS = {'.git', '.obsidian', '.trash', 'node_modules', '__pycache__'}
SENSITIVE_WORDS = ['seed', 'mnemonic', 'private key', 'password', 'wallet', 'keystore', 'recovery phrase', 'id_rsa']

def should_skip(path: Path) -> bool:
    lower = str(path).lower()
    if any(part in SKIP_DIR_PARTS for part in path.parts):
        return True
    if path.suffix.lower() not in {'.md', '.txt'}:
        return True
    return any(word in lower for word in SENSITIVE_WORDS)

def chunks(text: str):
    text = text[:MAX_FILE_CHARS]
    if len(text) <= CHUNK_SIZE:
        yield text.strip()
        return
    step = max(1, CHUNK_SIZE - CHUNK_OVERLAP)
    for i in range(0, len(text), step):
        chunk = text[i:i+CHUNK_SIZE].strip()
        if chunk:
            yield chunk

def embed(text: str):
    # Ollama embeddings endpoint. If unavailable, caller stores None and keyword search still works.
    payload = {'model': EMBED_MODEL, 'prompt': text[:4000]}
    req = urllib.request.Request(
        f'{OLLAMA_HOST}/api/embeddings',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    return data.get('embedding')

def title_for(path: Path, text: str) -> str:
    for line in text.splitlines():
        if line.startswith('#'):
            return line.strip('# ').strip()[:160]
    return path.stem

def main():
    if not VAULT.exists():
        raise SystemExit(f'Vault not found: {VAULT}')
    DB.parent.mkdir(parents=True, exist_ok=True)
    indexed = 0
    embedded = 0
    embed_failed = False

    with sqlite3.connect(DB) as con:
        for path in VAULT.rglob('*'):
            if not path.is_file() or should_skip(path):
                continue
            try:
                text = path.read_text(encoding='utf-8', errors='replace')
            except Exception:
                continue
            if not text.strip():
                continue
            title = title_for(path, text)
            for idx, chunk in enumerate(chunks(text)):
                h = hashlib.sha256((str(path) + str(idx) + chunk).encode('utf-8')).hexdigest()
                emb = None
                if not embed_failed:
                    try:
                        emb = embed(chunk)
                        embedded += 1
                    except Exception:
                        embed_failed = True
                con.execute(
                    """
                    INSERT INTO memory_chunks(source_path, source_type, title, chunk_text, embedding_json, chunk_hash)
                    VALUES (?, 'obsidian', ?, ?, ?, ?)
                    ON CONFLICT(chunk_hash) DO UPDATE SET
                        title=excluded.title,
                        chunk_text=excluded.chunk_text,
                        embedding_json=COALESCE(excluded.embedding_json, memory_chunks.embedding_json),
                        updated_at=CURRENT_TIMESTAMP
                    """,
                    (str(path), title, chunk, json.dumps(emb) if emb else None, h),
                )
                indexed += 1
    print(f'Indexed {indexed} chunks from {VAULT}')
    if embedded:
        print(f'Embedded {embedded} chunks with {EMBED_MODEL}')
    else:
        print('No embeddings stored. Ollama embedding model may be unavailable; keyword search still works.')

if __name__ == '__main__':
    main()
