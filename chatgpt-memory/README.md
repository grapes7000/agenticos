# ChatGPT Memory System

Safe local archive and resumable memory-extraction pipeline for the shared ChatGPT export.

## Safety boundaries

- Source export: `/home/lakota/Documents/mydata_chatgpt` — read only; never modified.
- Canonical state: `data/memory.sqlite3` (SQLite WAL, idempotent source IDs).
- Imported conversation text is untrusted data. The local model is explicitly instructed not to follow content instructions.
- Identity namespaces are isolated: `memory/lakota`, `memory/brooke`, `memory/shared`, `memory/unknown`.
- Only high-confidence Lakota technical/project candidate facts are extracted. Nothing is written into Hermes's built-in persistent memory automatically.
- Brooke archive is deliberately summary/tag oriented; its personal information is never promoted to Lakota.

## Components

- `src/chatgpt_memory.py`: deterministic parser/checkpoints/SQLite/Markdown rendering, local Ollama client, and a second-layer Lakota technical extractor.
- `data/memory.sqlite3`: canonical source provenance, results, attempts, lightweight index, and deep facts.
- `memory/lakota/knowledge/<project>.md`: generated consolidated durable knowledge by project; each item cites its conversation ID, source file, date, identity, and confidence.
- `STATUS.md`: generated live status.
- `memory/`: generated namespace views and Lakota project records.
- `systemd/chatgpt-memory-worker.service`: persistent user worker.

## Commands

After `bin/` is added to PATH:

- `chatgpt-memory-status`
- `chatgpt-memory-start`
- `chatgpt-memory-stop`
- `chatgpt-memory-resume`
- `chatgpt-memory-logs`
- `python3 src/chatgpt_memory.py deepen --limit 100` — enrich only LAKOTA-classified records that do not yet have a deep extraction; never re-ingests or reclassifies the export.
- `python3 src/chatgpt_memory.py search --query 'Hermes gateway Tailscale'` — returns durable facts first; if none match, returns the lightweight conversation index for routing to originals.
- `python3 src/chatgpt_memory.py show --conversation-id <uuid>` — opens the retained archived transcript only after search identifies a source.

## Two-layer retrieval

1. Search `deep_facts` / `memory/lakota/knowledge/` for source-backed, consolidated project knowledge.
2. If durable facts do not answer the question, search the one-sentence LAKOTA conversation index to find candidate conversations.
3. Inspect the original conversation transcript only when the durable fact/index needs more context. The source export remains read-only.

Deep extraction is deliberately restricted to already-classified LAKOTA records. BROOKE records retain the existing lightweight archive and are not promoted into Lakota knowledge.

Model: `qwen2.5:7b-instruct` through `OLLAMA_HOST=192.168.122.1:11434`.
