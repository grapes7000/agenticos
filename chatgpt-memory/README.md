# ChatGPT Memory System

Safe local archive, attachment recovery, identity routing, organization,
semantic discovery, and source-backed durable memory for ChatGPT exports.

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
- Atomic source-backed facts are preserved even when later consolidation groups,
  supersedes, suppresses, or disputes them.
- Nothing automatically writes extracted archive facts into Hermes persistent
  memory.

## Current architecture

The preferred pipeline is staged:

```text
Stage 0  archive import + attachments + embeddings
Stage 1  identity routing
Stage 2  summaries/tags/projects/type/importance
Stage 2B PCA -> UMAP -> DBSCAN semantic discovery + cluster labels
Stage 3  source-backed durable deep memory
```

Run/resume the complete pipeline with:

```bash
agentos-chatgpt-pipeline start
```

See `PIPELINE.md` for setup/runtime commands and
`../docs/CHATGPT_MEMORY_STAGE3_PLAN.md` for the Stage-3 design contract.

## Stage 0 — Archive and attachment indexing

The importer handles conversations and exported files:

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

The importer honors `OLLAMA_HOST` and `AGENTOS_EMBED_MODEL`. The modern
`/api/embed` endpoint is preferred with truncation enabled; legacy
`/api/embeddings` remains a compatibility fallback.

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
a local Ollama model. Identity routing does not mark a conversation as fully
analyzed and does not extract durable memory.

## Stage 2 — Lightweight organization

`src/organize_fast.py` consumes the resolved identity and stores:

- one-sentence summary;
- tags;
- projects;
- conversation type;
- importance score.

It never re-decides identity and does not perform deep fact extraction.

## Stage 2B — Semantic discovery

`src/semantic_cluster.py` reads existing `chat_chunks.embedding_json` values
directly from SQLite and builds one normalized vector per conversation before
PCA -> UMAP -> DBSCAN. A separate 2-D UMAP is generated only for visualization.

`src/label_semantic_clusters.py` labels discovered clusters using representative
Stage-2 summaries. Oversized Stage-2 categories can be clustered independently
to discover useful subcategories.

Clustering runs are retained in:

```text
semantic_cluster_runs
conversation_reductions
semantic_clusters
```

## Stage 3 — Durable deep memory

### Extraction foundation

`src/deep_memory.py` implements Stages 3.1-3.4:

- priority/resumable passage queue;
- turn-aware passage construction with stable message refs;
- strict structured local-model extraction;
- source-backed `knowledge_items`;
- many-to-many project routing;
- `knowledge_evidence` provenance;
- assistant-only claim blocking;
- explicit user success confirmation for `confirmed_solution`;
- error -> failed attempt -> confirmed solution chains;
- decision -> decision reason relations.

### Consolidation and temporal state

`src/deep_memory_finalize.py` implements Stages 3.5-3.7:

- conservative duplicate groups without deleting atomic facts;
- explicit current/historical/superseded handling;
- deterministic `supersedes` relations when the source already establishes the
  temporal transition;
- `knowledge_conflicts` for competing state claims;
- `knowledge_review_queue` for ambiguous/blocked material;
- durable `knowledge_overrides` for user corrections;
- cluster-aware project snapshots;
- generated namespace/project Markdown views.

Important tables include:

```text
deep_memory_runs
deep_memory_extractions
deep_memory_candidates
knowledge_items
knowledge_item_projects
knowledge_evidence
knowledge_relations
knowledge_groups
knowledge_group_members
knowledge_conflicts
knowledge_review_queue
knowledge_overrides
project_memory_snapshots
```

### Full Stage-3 runner

`src/run_stage3.py` resumes all Stage-3 work in bounded batches, then finalizes
and renders the successful results. The main `agentos-chatgpt-pipeline` invokes
this runner automatically after Stage-2B clustering.

Generated views live under:

```text
chatgpt-memory/memory/<namespace>/projects/<project>/
```

They are disposable/rebuildable views of SQLite, not the canonical memory.

## Unified memory search

`agentos-memory-search` now searches consolidated durable knowledge by default,
then raw ChatGPT chunks, recovered attachment chunks, and Obsidian memory.
Durable canonical facts receive priority when they directly match the query;
raw semantic recall remains available for source inspection.

```bash
agentos-memory-search "vpn problem that broke ssh"
agentos-memory-search --durable "AgenticOS database path"
agentos-memory-search --chatgpt "tailscale mullvad remote access"
agentos-memory-search --assets "pink desktop screenshot"
agentos-memory-search --obsidian "AgenticOS architecture"
```

The preferred retrieval ladder is:

1. consolidated current durable project memory;
2. source-backed atomic knowledge items;
3. semantic ChatGPT/attachment/Obsidian recall;
4. original transcript or recovered asset when full evidence is needed.

## Project/knowledge foundation

`src/knowledge_index.py` remains the durable project/index foundation:

- `projects`;
- `conversation_projects`;
- `knowledge_items`;
- FTS5 search over source-backed project knowledge.

Legacy `deep_facts` and `project_facts` remain migration inputs.

## Legacy deep extractors

`src/chatgpt_memory.py` still contains earlier commands such as:

```bash
python3 src/chatgpt_memory.py deepen --limit 100
python3 src/chatgpt_memory.py expand-projects
```

These remain useful for inspecting/migrating previous work, but they are not the
preferred architecture for new deep-memory extraction.
