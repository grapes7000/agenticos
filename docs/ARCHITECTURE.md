# AgenticOS architecture

## Supported core

The supported core has five layers:

1. `settings.py` resolves paths and local service configuration.
2. `database.py` owns the AgenticOS SQLite schema and migrations.
3. `workflows.py` gathers read-only status and produces maintenance advice.
4. `dashboard.py` renders the same structured status as HTML.
5. `cli.py` exposes these capabilities through one stable command tree.

Every supported command should return or render structured data. Human reports
and the dashboard are views of that data, not separate sources of truth.

## Safety model

- Inspection is read-only by default.
- Maintenance commands produce proposals, never automatic deletions.
- Commands use argument arrays rather than shell interpolation.
- Private exports, databases, logs, and generated reports never belong in Git.
- Optional external tools are detected and reported without making them hard
  dependencies.

## Compatibility layer

The older scripts remain callable from `agentos legacy <command>`. Selected
well-known commands such as `health`, `security`, and `openclaw-prep` are also
forwarded directly. New supported-core features should be added to `agenticos/`
rather than by adding unrelated shell wrappers.

The ChatGPT archive pipeline is a deliberate exception: it has its own private
data model and long-running local-AI stages, so it remains under
`chatgpt-memory/` with the orchestration wrapper
`bin/agentos-chatgpt-pipeline`.

## Data ownership

The supported AgenticOS database is `settings.database_path`. The default is
`~/.local/share/agenticos/agentos.sqlite3`.

The ChatGPT memory archive keeps a separate database because it has different
provenance, privacy, vector-storage, and rebuild requirements:

```text
chatgpt-memory/data/memory.sqlite3
```

The CLI may discover/query that archive, but the archive pipeline remains the
owner of its schema and derived state.

## ChatGPT memory subarchitecture

The ChatGPT memory system is staged so cheap/routing work is separated from
expensive durable-memory extraction:

```text
Stage 0
  archive ingest
  attachments
  chunk embeddings
      |
Stage 1
  identity_classifications
      |
Stage 2
  conversation_organizations
      |
Stage 2B
  PCA -> UMAP -> DBSCAN
  semantic_cluster_runs
  semantic_clusters
      |
Stage 3 (planned)
  source-backed deep extraction
  project routing
  evidence / relations / conflicts
  consolidated current state
```

Important design rules:

- identity is an upstream routing decision and is not re-decided by deep memory;
- Stage-2 summaries/tags are organization hints, not durable facts;
- semantic clusters help group related conversations but are not evidence;
- source transcripts/attachments remain the evidence layer;
- SQLite is canonical; CSV and Markdown are rebuildable views;
- deep-memory consolidation must preserve historical/superseded state and
  contradictory evidence.

The existing `knowledge_index.py` project/knowledge schema is the foundation for
Stage 3 rather than creating a separate competing project index.

See:

- `docs/CHATGPT_MEMORY_PLAN.md`;
- `docs/CHATGPT_MEMORY_STAGE3_PLAN.md`;
- `chatgpt-memory/PIPELINE.md`.
