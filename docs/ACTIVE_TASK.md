# Active Task

## CHATGPT-MEMORY-3.1 — Deep-memory schema and resumable queue

**Area:** ChatGPT memory pipeline

**Status:** TODO

## Outcome

Create the Stage-3 foundation without performing deep LLM extraction yet.

At the end of this slice, AgenticOS should be able to determine which organized
conversations need deep-memory processing, assign them stable priorities, track
passage-level extraction state, resume interrupted work, and invalidate only
work derived from a changed conversation.

## Inputs

Use existing upstream state only:

- `conversations`;
- `identity_classifications`;
- `conversation_organizations`;
- semantic cluster membership where available;
- existing conversation content hashes.

Do not re-run identity or organization inside Stage 3.

## Scope

Implement the Stage-3 run/queue schema described in
`CHATGPT_MEMORY_STAGE3_PLAN.md`, including the equivalent of:

```text
deep_memory_runs
deep_memory_extractions
```

The queue should prioritize high-value conversations using importance, project
membership, conversation type, cluster coverage, and recency/current-state
signals while still allowing lower-priority conversations to be processed
later.

## Required behavior

- queue creation is deterministic for the same database state;
- completed unchanged passages are reused;
- failed/interrupted rows can resume;
- source changes invalidate only affected Stage-3 derived work;
- identity namespace is carried into Stage 3 but never rewritten;
- status output shows queued/completed/failed/remaining counts;
- no LLM extraction is performed in this slice.

## Tests

Add tests for:

- schema creation on an existing archive DB;
- deterministic prioritization;
- resumability after an interrupted item;
- no duplicate queue rows on rerun;
- changed-conversation invalidation;
- unchanged-conversation reuse;
- identity namespace preservation.

## Explicitly out of scope

Do not implement yet:

- the Stage-3 LLM prompt;
- knowledge-item extraction;
- semantic deduplication;
- conflict resolution;
- project snapshot generation;
- Markdown rendering;
- Hermes memory promotion.

## Review boundary

Stop after Stage 3.1 passes its tests. Review the schema, priority behavior,
content-hash invalidation, and resume semantics before starting Stage 3.2.
