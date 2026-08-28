# Current State

## Current milestone

Checkpoint 1 is ready to begin. Planning and architecture are defined; implementation has not started.

## What is decided

- AgenticOS is a Python-based Linux control utility.
- The CLI is built to completion before TUI/Qt work becomes a primary focus.
- Checks are read-only and return structured results.
- Actions are a separate future state-changing layer.
- Rich is the initial CLI presentation layer.
- Qwen/local chat models write small self-contained slices without needing repository access for the first five checkpoints.
- ChatGPT reviews and explains the whole checkpoint after all lettered tasks are complete.

## Active work

`BUILD-001A` — bootstrap package and `agent` CLI entry point.

## Next review boundary

After BUILD-001A through BUILD-001F are complete and `agent status` works with passing tests, stop before Checkpoint 2 and perform a full checkpoint review.
