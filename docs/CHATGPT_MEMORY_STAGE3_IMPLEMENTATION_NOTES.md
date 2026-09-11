# Stage 3.1–3.4 Implementation Notes

Implementation lives in `chatgpt-memory/src/deep_memory.py` and is intentionally separate from the main pipeline until Stage 3.8.

Key invariants:

- identity is read from `identity_classifications` and never rewritten;
- assistant-only claims remain blocked candidates;
- confirmed solutions require user-authored success evidence;
- unchanged completed passages are reused by passage/source hash;
- changed passages selectively invalidate their Stage-3 derived evidence/items;
- knowledge items retain namespace, project membership, source conversation, passage, and message evidence refs;
- relation building is conservative and limited to within-conversation chains until Stage 3.5+ adds broader deduplication and temporal/conflict logic.

Do not begin Stage 3.5 until the local tests and queue/status smoke test have been reviewed.
