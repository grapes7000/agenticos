# ChatGPT Memory System

Safe local archive, attachment recovery, identity routing, organization,
semantic discovery, and planned deep memory for ChatGPT exports.

## Safety boundaries

- Source exports are read-only. The importer never renames, edits, or executes
  files from an export.
- Canonical ChatGPT state is `data/memory.sqlite3`.
- ZIP exports are unpacked into a SHA-addressed cache under
  `~/.local/share/agenticos/chatgpt-imports/`.
- Generic `.dat` attachments are MIME-sniffed and exposed through
  extension-correct symlinks under `~/.local/share/agenticos/chatgpt-assets/`;
  the raw blobs remain untouched.
- Imported conversation text and extracted attachment text are untrusted data.
- Identity routing is stored separately from later organization and memory
  extraction.
- Brooke, Lakota, shared, and unknown material remain separate namespaces.
- Semantic clusters are organizational context, not factual evidence.
- Nothing automatically writes extracted archive facts into Hermes persistent
  memory.

## Current architecture

The preferred pipeline is staged:

```text
Stage 0  archive import + attachments + embeddings
Stage 1  identity routing
Stage 2  summaries/tags/projects/type/importance
Stage 2B PCA -> UMAP -> DBSCAN semantic discovery + cluster labels
Stage 3  deep durable memory (planned; not yet implemented)
```

Run/resume Stages 0–2B with:

```bash
agentos-chatgpt-pipeline start
```

See `PIPELINE.md` for setup and runtime commands and
`../docs/CHATGPT_MEMORY_STAGE3_PLAN.md` for the Stage-3 design.

## Stage 0 — Archive and attachment indexing

The importer handles both conversations and exported files:

- conversations are flattened using the active conversation branch, chunked on
  message/turn boundaries, and embedded with `AGENTOS_EMBED_MODEL` (default
  `nomic-embed-text`);
- re-imports compare per-conversation content hashes;
- unchanged conversations retain their vectors and derived state;
- changed conversations invalidate only stale dependent rows;
- `.dat` and `file_*` assets are identified from their contents rather than
  their extension;
- text, JSON, CSV, shell/Python/C source, DOCX, ZIP listings, and PDF text (when
  `pdftotext` is installed) become searchable text;
- asset references are linked back to conversation/message provenance;
- images, audio, and video with conversation linkage receive contextual text
  embeddings from surrounding conversation context. These are not true
  pixel/audio/video-content embeddings.

One-command import:

```bash
agentos-chatgpt-import ~/Downloads/chatgpt-export.zip
agentos-chatgpt-import ~/Documents/mydata_chatgpt
```

Useful direct importer commands:

```bash
cd ~/AgenticOS/chatgpt-memory
python3 src/chatgpt_archive.py status
python3 src/chatgpt_archive.py import ~/Downloads/chatgpt-export.zip
python3 src/chatgpt_archive.py import ~/Documents/mydata_chatgpt --no-embeddings
```

The importer honors:

- `OLLAMA_HOST` — Ollama base URL, with or without `http://`;
- `AGENTOS_EMBED_MODEL` — embedding model, default `nomic-embed-text`.

The modern `/api/embed` endpoint is preferred with truncation enabled; legacy
`/api/embeddings` is retained as a compatibility fallback.

## Stage 1 — Identity routing

`src/identify_fast.py` stores one separate identity classification per
conversation in `identity_classifications`:

```text
LAKOTA
BROOKE
SHARED
UNKNOWN
```

The first phase uses deterministic signals. Ambiguous conversations are sent to
a local Ollama model. A decisive recheck mode can be used for conversations
that were previously left unknown.

Identity routing does not mark a conversation as fully analyzed and does not
extract durable memories.

## Stage 2 — Lightweight organization

`src/organize_fast.py` consumes the resolved identity and stores, separately:

- one-sentence summary;
- tags;
- projects;
- conversation type;
- importance score.

It never re-decides identity and does not perform deep fact extraction.

## Stage 2B — Semantic discovery

`src/semantic_cluster.py` reads the existing `chat_chunks.embedding_json` values
directly from SQLite.

For each conversation it:

1. normalizes each chunk vector;
2. mean-pools all chunks in that conversation;
3. normalizes the resulting conversation vector;
4. applies PCA;
5. applies UMAP in a higher-dimensional clustering representation;
6. runs DBSCAN in that representation;
7. builds a separate 2-D UMAP only for visualization/export.

`src/label_semantic_clusters.py` labels discovered clusters using representative
Stage-2 summaries. Oversized Stage-2 categories can be clustered independently
to discover useful subcategories.

Clustering runs are retained in:

```text
semantic_cluster_runs
conversation_reductions
semantic_clusters
```

They can also be exported as CSV without making CSV the source of truth.

## Unified semantic search

`agentos-memory-search` searches Obsidian memory, ChatGPT conversation chunks,
and recovered attachment chunks together using keyword + cosine-similarity
ranking.

```bash
agentos-memory-search "vpn problem that broke ssh"
agentos-memory-search --chatgpt "tailscale mullvad remote access"
agentos-memory-search --assets "pink desktop screenshot"
agentos-memory-search --obsidian "AgenticOS architecture"
agentos-memory-search --chatgpt --assets "wacom configuration script"
```

Search results retain conversation IDs, message ranges, asset IDs, MIME types,
and source/recovered paths so results can be traced to the original archive.

## Project/knowledge index foundation

`src/knowledge_index.py` provides the durable project/index foundation that
Stage 3 will extend:

- `projects`;
- `conversation_projects`;
- `knowledge_items`;
- FTS5 search over source-backed project knowledge;
- rebuildable Markdown project dossiers.

Legacy `deep_facts` and `project_facts` can be normalized into this index.

## Legacy deep extractors

`src/chatgpt_memory.py` still contains earlier commands such as:

```bash
python3 src/chatgpt_memory.py deepen --limit 100
python3 src/chatgpt_memory.py expand-projects
```

These remain useful for inspecting/migrating previous work, but they are **not
the preferred design for new deep-memory extraction**. Stage 3 will replace the
monolithic flow with a source-backed, resumable passage-level pipeline that
uses the identity, organization, and semantic-cluster context already produced
by Stages 1–2B.

## Planned Stage 3 retrieval ladder

The target retrieval order is:

1. consolidated current durable project memory;
2. source-backed atomic knowledge items;
3. semantic search across ChatGPT/attachment chunks and Obsidian memory;
4. original transcript or recovered asset when full evidence is needed.

Full plan:

```text
../docs/CHATGPT_MEMORY_STAGE3_PLAN.md
```
