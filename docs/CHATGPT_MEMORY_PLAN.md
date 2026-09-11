# ChatGPT Memory Plan

## Goal

Turn private ChatGPT exports into a local, source-backed memory system where:

- every conversation and attachment remains traceable to its source;
- Brooke, Lakota, shared, and unknown material remain separated by namespace;
- conversations can belong to multiple projects and semantic topics;
- broad categories can be refined by semantic clustering;
- durable memory distinguishes errors, failed attempts, confirmed fixes,
  decisions, configuration, state, workflows, and lessons;
- current and historical facts can coexist without silently overwriting one
  another;
- raw exports remain read-only.

## Current staged architecture

### Stage 0 — Archive ingest and semantic indexing — implemented

`chatgpt_archive.py` handles:

- incremental ZIP or extracted-directory import;
- conversation content hashing and changed-source invalidation;
- turn-aware conversation chunking;
- Ollama embeddings (`nomic-embed-text` by default);
- attachment discovery, SHA deduplication, MIME recovery, and text extraction;
- attachment-to-conversation provenance;
- semantic indexing of conversation and attachment text/context.

Canonical archive state is:

```text
chatgpt-memory/data/memory.sqlite3
```

### Stage 1 — Identity routing — implemented

`identify_fast.py` stores identity separately in `identity_classifications`.

Identity is limited to:

```text
LAKOTA
BROOKE
SHARED
UNKNOWN
```

The pass uses deterministic signals first and a local Ollama model only for
ambiguous conversations. Identity is independent from later organization and
deep-memory extraction.

### Stage 2 — Lightweight organization — implemented

`organize_fast.py` consumes the identity table and stores:

- one-sentence summary;
- tags;
- project hints;
- conversation type;
- importance score.

It does not extract durable facts and does not re-decide identity.

### Stage 2B — Semantic discovery and category refinement — implemented

`semantic_cluster.py` reads existing conversation chunk embeddings directly from
SQLite and builds one normalized mean-pooled vector per conversation.

The discovery pipeline is:

```text
conversation chunk embeddings
-> normalize chunks
-> mean-pool per conversation
-> normalize conversation vector
-> PCA
-> UMAP in higher-dimensional clustering space
-> DBSCAN
```

A separate 2-D UMAP is used only for visualization/export. DBSCAN is not run on
the 2-D visualization representation.

`label_semantic_clusters.py` assigns human-readable labels to discovered
clusters using representative Stage-2 summaries. Oversized Stage-2 categories
can be clustered again within their own scope so broad buckets such as
`troubleshooting` or `design_creative` can split into useful subtopics.

All clustering runs are retained independently in SQLite and may also be
exported as CSV.

### Pipeline runner — implemented

`bin/agentos-chatgpt-pipeline` wraps Stages 0–2B into one resumable workflow.

It can:

- start from a new export with `--source`;
- resume an existing database;
- skip completed identity and organization work;
- run in detached tmux;
- install clustering dependencies into its own virtual environment;
- reuse existing semantic runs or create fresh runs;
- automatically refine categories above `--large-min`;
- label semantic clusters and export CSV maps.

See `chatgpt-memory/PIPELINE.md` for commands.

## Existing knowledge-index foundation

`knowledge_index.py` already provides a non-destructive source-backed project
index:

- `projects` — canonical project names and aliases;
- `conversation_projects` — many-to-many conversation/project routing;
- `knowledge_items` — atomic source-backed knowledge grouped by category;
- FTS5 search over project knowledge;
- generated project dossiers.

Legacy `deep_facts` and `project_facts` can be imported into that foundation,
but the older all-in-one `chatgpt_memory.py process/deepen/expand-projects`
workflow is no longer the preferred architecture for new extraction work.

## Stage 3 — Deep memory — planned, not yet implemented

Stage 3 is the remaining major layer. It will use identity, organization,
project hints, semantic-cluster context, and the original source transcript to
extract and consolidate durable memory.

It will cover:

- project/system state;
- decisions and reasons;
- errors and failed approaches;
- confirmed solutions with explicit success evidence;
- configuration and workflows;
- lessons and durable facts;
- temporal state and supersession;
- conservative deduplication;
- contradiction/review handling;
- per-identity project dossiers;
- integration with durable-memory search.

The implementation plan is maintained in:

```text
docs/CHATGPT_MEMORY_STAGE3_PLAN.md
```

## Retrieval model

The intended retrieval ladder is:

1. consolidated current durable project memory;
2. source-backed atomic knowledge items;
3. semantic search across raw ChatGPT conversation and attachment chunks;
4. original transcript or recovered asset for full source inspection.

Semantic clusters are organizational context, not factual evidence. Durable
claims must always point back to source conversations/evidence.

## Safety and quality rules

- Raw conversation/attachment content is untrusted input.
- Source exports are never edited.
- Identity namespaces are not silently mixed.
- Assistant suggestions do not become successful fixes without source evidence
  that they worked.
- Contradictory facts are preserved and resolved explicitly rather than silently
  overwritten.
- Reruns must be idempotent for unchanged source material.
- A changed conversation invalidates only derived memory that depends on it.
- Generated Markdown is a rebuildable view of SQLite, not a second source of
  truth.
