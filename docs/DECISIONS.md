# Decisions

## D-001 — CLI first

Build a complete, useful CLI/backend before investing in a TUI or PySide6/Qt GUI. Future interfaces consume the same Python APIs.

## D-002 — Checks and actions are separate concepts

Checks are read-only. State-changing behavior will later use an explicit action layer rather than hiding mutations inside diagnostics.

## D-003 — Structured results, not booleans

Checks return a shared structured result with at least HEALTHY, DEGRADED, and BROKEN states plus human-readable summary/detail. This avoids ambiguous booleans such as `True` meaning either "healthy" or "condition detected".

## D-004 — One command runner

External process execution is centralized behind a bounded subprocess helper with finite timeouts and normalized execution failures.

## D-005 — Deterministic facts before AI explanation

Python/system evidence owns factual state and severity. Ollama may later explain already-established results conversationally but should not replace deterministic diagnostics.

## D-006 — Rich for initial CLI presentation

Use Rich for compact readable terminal output. Checks remain UI-independent.

## D-007 — Checkpoint review workflow

Local Qwen writes small self-contained tasks. The developer completes all lettered tasks in a checkpoint and tests them locally. ChatGPT then reviews and explains the completed checkpoint before the next checkpoint begins.

## D-008 — Local model should not require repo context for early proof tasks

For Checkpoints 1–5, Qwen prompts should contain enough interface and behavior detail to write the requested slice without uploaded repository files or planning documents. When a later task truly depends on existing implementation details, provide only the smallest necessary code excerpt.

## D-009 — Mullvad route source matters

Network diagnostics must distinguish "Mullvad is present" from "traffic is actually exiting through Mullvad" and should distinguish local Mullvad VPN/tunnel routing from a Tailscale-provided Mullvad exit path when deterministic evidence supports it.

## D-010 — Daily use drives post-v1 expansion

After CLI/TUI/GUI foundations exist, newly encountered Linux command recipes should be evaluated as reusable AgenticOS checks/actions. New capability lands in the backend/CLI first, then appears in visual interfaces.
