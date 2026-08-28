# Prompt — Update Project State and Handoff

```text
Using the completed task, final code/diff, and actual verification output I provide, update the durable project-state documents.

Return complete replacement content only for files that genuinely need changes:
- docs/CURRENT_STATE.md
- docs/AI_HANDOFF.md
- docs/DECISIONS.md if a durable decision changed
- docs/BUGS.md if an unresolved defect was discovered
- docs/CHANGELOG.md if user-visible behavior changed

Rules:
- do not invent tests or claim verification that did not happen;
- keep AI_HANDOFF short enough for a fresh chat to read quickly;
- record current facts, not a transcript of our conversation;
- preserve unresolved problems explicitly;
- identify the next legal task from TASKS.md, but do not activate it or begin implementation.
```
