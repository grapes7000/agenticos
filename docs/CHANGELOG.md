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
  chunks, and indexed ChatGPT attachments.
- Separate fast identity-routing stage stored in `identity_classifications`.
- Lightweight conversation-organization stage stored in
  `conversation_organizations`.
- Semantic discovery directly from existing SQLite embeddings using
  mean-pooled conversation vectors, PCA, UMAP, and DBSCAN.
- Independent 2-D UMAP coordinates for visualization/export without clustering
  in the visualization space.
- Local-model labels for semantic clusters.
- Scoped semantic subclustering for oversized Stage-2 categories.
- CSV export of semantic clustering runs.
- Resumable `agentos-chatgpt-pipeline` runner with one-time dependency setup,
  tmux execution, status/log/attach commands, and fresh-export or existing-DB
  workflows.
- Stage-3 deep-memory architecture and implementation plan.

### Changed

- Re-importing an export reuses unchanged semantic vectors and preserves
  existing derived memory instead of rebuilding everything.
- Ollama embedding calls prefer `/api/embed` with truncation and retry transient
  server failures; the legacy endpoint remains a compatibility fallback.
- ChatGPT memory processing is now documented as staged identity -> organization
  -> semantic discovery -> deep memory rather than one monolithic classifier and
  extractor.
- Legacy deep extractors remain available for migration/reference but are no
  longer the preferred architecture for new deep-memory work.

### Fixed

- Identity status/recheck behavior no longer needs to resurrect cleared legacy
  `UNKNOWN` classifications as part of the preferred workflow.
- Archive embedding resilience for oversized/problematic chunks and transient
  Ollama HTTP failures.

### Removed

- None.
