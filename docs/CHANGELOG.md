# Changelog

Track meaningful user-visible changes. Use Git history for low-level
implementation detail.

## Unreleased

### Added

- Incremental ChatGPT export importer for ZIP files or extracted directories,
  with per-conversation change detection and conversation-aware semantic
  embeddings.
- ChatGPT attachment indexing with `.dat` MIME recovery, SHA deduplication,
  text/document extraction, conversation/message provenance, and
  extension-correct recovered asset links.
- Unified hybrid semantic search across Obsidian memory, ChatGPT conversation
  chunks, indexed ChatGPT attachments, and consolidated durable knowledge.
- Separate fast identity-routing stage stored in `identity_classifications`.
- Lightweight conversation-organization stage stored in
  `conversation_organizations`.
- Semantic discovery directly from existing SQLite embeddings using
  mean-pooled conversation vectors, PCA, UMAP, and DBSCAN.
- Independent 2-D UMAP coordinates for visualization/export without clustering
  in the visualization space.
- Local-model labels for semantic clusters and scoped semantic subclustering for
  oversized Stage-2 categories.
- CSV export of semantic clustering runs.
- Resumable `agentos-chatgpt-pipeline` runner with dependency setup, tmux
  execution, status/log/attach commands, and fresh-export or existing-DB
  workflows.
- Stage 3.1 content-aware/resumable deep-memory passage queue.
- Stage 3.2 turn-aware structured extraction with stable user/assistant evidence
  refs.
- Stage 3.3 source-backed atomic knowledge writing with many-to-many projects and
  namespace preservation.
- Stage 3.4 explicit success confirmation plus error/attempt/fix and
  decision/reason relations.
- Stage 3.5 conservative duplicate groups, temporal supersession,
  `knowledge_conflicts`, review queue, and durable user overrides.
- Stage 3.6 cluster-aware project consolidation into rebuildable
  `project_memory_snapshots`.
- Stage 3.7 generated per-namespace project Markdown views and durable-first
  memory search.
- Stage 3.8 full Stage-3 orchestration through `run_stage3.py` and integration
  into the main ChatGPT pipeline.

### Changed

- Re-importing an export reuses unchanged semantic vectors and preserves
  existing derived memory instead of rebuilding everything.
- Ollama embedding calls prefer `/api/embed` with truncation and retry transient
  server failures; the legacy endpoint remains a compatibility fallback.
- ChatGPT memory processing is now staged identity -> organization -> semantic
  discovery -> source-backed deep memory rather than one monolithic classifier
  and extractor.
- `agentos-memory-search` now prefers consolidated durable knowledge when it
  matches the query while retaining raw semantic recall for source inspection.
- Legacy deep extractors remain available for migration/reference but are no
  longer the preferred architecture.

### Fixed

- Identity status/recheck behavior no longer needs to resurrect cleared legacy
  `UNKNOWN` classifications as part of the preferred workflow.
- Archive embedding resilience for oversized/problematic chunks and transient
  Ollama HTTP failures.
- Deep-memory consolidation no longer needs to overwrite or delete atomic source
  facts in order to deduplicate or resolve current-state views.

### Removed

- None.
