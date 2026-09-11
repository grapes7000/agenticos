# ChatGPT Memory System

Safe local archive, attachment recovery, and resumable semantic-memory pipeline for ChatGPT exports.

## Safety boundaries

- Source exports are read-only. The importer never renames, edits, or executes files from an export.
- Canonical ChatGPT state is `data/memory.sqlite3` (SQLite WAL, idempotent source IDs and chunk hashes).
- ZIP exports are unpacked into a SHA-addressed cache under `~/.local/share/agenticos/chatgpt-imports/`.
- Generic `.dat` attachments are MIME-sniffed and exposed through extension-correct symlinks under `~/.local/share/agenticos/chatgpt-assets/`; the raw blobs remain untouched.
- Imported conversation text and extracted attachment text are untrusted data.
- Identity namespaces remain isolated: `memory/lakota`, `memory/brooke`, `memory/shared`, `memory/unknown`.
- Only high-confidence Lakota technical/project candidate facts are promoted into the existing deep-memory layers. Brooke archive material remains summary/tag oriented.

## What is indexed

The archive importer handles both conversations and exported files:

- ChatGPT conversations are flattened using the active conversation branch, chunked on message/turn boundaries, and embedded with `AGENTOS_EMBED_MODEL` (default `nomic-embed-text`).
- Re-imports compare per-conversation content hashes. Unchanged conversations keep their existing analysis and vectors; changed conversations invalidate only their stale derived rows and return to the normal processing queue.
- `.dat` and `file_*` assets are identified from their contents rather than their extension.
- Text, JSON, CSV, shell/Python/C source, DOCX, ZIP listings, and PDF text (when `pdftotext` is installed) become searchable text.
- Asset references are linked back to conversation/message provenance when the ChatGPT JSON contains matching file IDs.
- Images, audio, and video that have conversation linkage receive embeddings for their surrounding conversation context. **These are contextual text embeddings, not true pixel/audio/video-content embeddings.** The binary assets are still inventoried and recoverable by their real file type.

## One-command incremental import

After `bin/` is on your PATH:

```bash
agentos-chatgpt-import ~/Downloads/chatgpt-export.zip
```

An already-extracted export directory works too:

```bash
agentos-chatgpt-import ~/Documents/mydata_chatgpt
```

The command performs, in order:

1. safe ZIP staging when needed;
2. incremental conversation ingest/update detection;
3. conversation-aware semantic chunking and vector generation;
4. attachment discovery and MIME recovery;
5. document/code/text extraction where supported;
6. asset-to-conversation provenance linking;
7. extension-correct recovered asset symlinks;
8. semantic indexing of extracted attachment text or linked conversation context.

Re-running the same export is safe: unchanged conversation vectors and attachment content are reused instead of rebuilding the entire index.

Useful importer commands from `chatgpt-memory/`:

```bash
python3 src/chatgpt_archive.py status
python3 src/chatgpt_archive.py import ~/Downloads/chatgpt-export.zip
python3 src/chatgpt_archive.py import ~/Documents/mydata_chatgpt --no-embeddings
```

The importer honors:

- `OLLAMA_HOST` — Ollama base URL, with or without `http://`;
- `AGENTOS_EMBED_MODEL` — embedding model, default `nomic-embed-text`.

It supports both Ollama's `/api/embeddings` and `/api/embed` embedding endpoints.

## Unified semantic search

`agentos-memory-search` now searches Obsidian memory, ChatGPT conversation chunks, and recovered attachment chunks together using keyword + cosine similarity ranking.

```bash
agentos-memory-search "vpn problem that broke ssh"
agentos-memory-search --chatgpt "tailscale mullvad remote access"
agentos-memory-search --assets "pink desktop screenshot"
agentos-memory-search --obsidian "AgenticOS architecture"
agentos-memory-search --chatgpt --assets "wacom configuration script"
```

If no source-selection flag is supplied, all three indexes are searched. Search results retain conversation IDs, message ranges, asset IDs, MIME types, and source/recovered paths so a result can be traced back to the original export.

## Existing deep-memory pipeline

The semantic archive complements, rather than replaces, the existing structured memory pipeline:

- `src/chatgpt_memory.py`: deterministic parser/checkpoints/SQLite/Markdown rendering, local Ollama classifier, and Lakota technical extractors.
- `src/chatgpt_archive.py`: incremental export/asset ingestion and semantic-vector indexing.
- `data/memory.sqlite3`: canonical source provenance, processing state, semantic chunks, attachment metadata, and deep facts.
- `memory/lakota/knowledge/<project>.md`: generated consolidated durable knowledge by project with provenance.
- `STATUS.md`: generated live status.
- `systemd/chatgpt-memory-worker.service`: persistent existing classification/extraction worker.

Existing commands remain available:

```bash
python3 src/chatgpt_memory.py deepen --limit 100
python3 src/chatgpt_memory.py search --query 'Hermes gateway Tailscale'
python3 src/chatgpt_memory.py show --conversation-id <uuid>
python3 src/chatgpt_memory.py expand-projects
```

The retrieval ladder is therefore:

1. structured durable project facts for concise established knowledge;
2. semantic search across Obsidian, raw ChatGPT conversation chunks, and attachment text/context;
3. the retained original conversation transcript or raw asset when deeper inspection is needed.

Nothing in the archive importer automatically writes extracted facts into Hermes persistent memory.
