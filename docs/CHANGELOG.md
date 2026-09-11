# Changelog

Track meaningful user-visible changes. Use Git history for low-level implementation detail.

## Unreleased

### Added

- Incremental ChatGPT export importer for ZIP files or extracted directories, with per-conversation change detection and conversation-aware semantic embeddings.
- ChatGPT attachment indexing with `.dat` MIME recovery, text/document extraction, conversation/message provenance, and extension-correct recovered asset links.
- Unified hybrid semantic search across Obsidian memory, ChatGPT conversation chunks, and indexed ChatGPT attachments.

### Changed

- Re-importing an export reuses unchanged semantic vectors and preserves existing derived memory instead of rebuilding everything.

### Fixed

### Removed
