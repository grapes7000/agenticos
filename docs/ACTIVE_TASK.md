# Active Task

## CHATGPT-MEMORY-3.1–3.4 — Deep-memory extraction foundation

**Area:** ChatGPT memory pipeline

**Status:** IMPLEMENTED — awaiting local test run/review before Stage 3.5

## Completed scope

Stages 3.1 through 3.4 are implemented in `chatgpt-memory/src/deep_memory.py`.

### 3.1 — Schema and resumable queue

Implemented:

- `deep_memory_runs` and passage-level `deep_memory_extractions`;
- queue priority from Stage-2 importance, project membership, conversation type,
  global semantic-cluster membership/representatives, recency, and attachment
  references;
- content-hash/passage-hash reuse for unchanged work;
- selective invalidation for changed passages/conversations;
- interrupted `processing` rows reset to resumable `queued` state;
- retry handling and status output.

### 3.2 — Structured passage extractor

Implemented:

- bounded turn-aware passages with small overlap;
- stable message refs such as `u0001` and `a0002` for provenance;
- strict Ollama JSON schema;
- retry/timeout behavior;
- atomic memory categories from the Stage-3 plan;
- evidence refs and explicit success-evidence refs;
- no cross-conversation consolidation.

### 3.3 — Project routing and knowledge writer

Implemented:

- Stage-2 project hints combined with passage-level project hints;
- many-to-many conversation/project routing;
- many-to-many knowledge-item/project routing;
- source-backed writes into the existing `knowledge_items` foundation;
- namespace preservation (`lakota`, `brooke`, `shared`, `unknown`);
- dedicated `knowledge_evidence` records with passage/message provenance;
- Stage-3 origin marking without rewriting legacy knowledge.

### 3.4 — Relations, success confirmation, and error chains

Implemented:

- assistant-only claims are retained as blocked candidates rather than promoted;
- `confirmed_solution` requires user-authored success evidence;
- failed approaches remain distinct from confirmed solutions;
- deterministic within-conversation links:
  - `error -> failed_approach`;
  - `error -> confirmed_solution`;
  - `decision -> decision_reason`;
- `knowledge_relations` stores the chains without deleting source items.

## CLI

Standalone command:

```bash
agentos-chatgpt-deep-memory queue
agentos-chatgpt-deep-memory extract --limit 25
agentos-chatgpt-deep-memory write
agentos-chatgpt-deep-memory link
agentos-chatgpt-deep-memory status
```

`process` combines extract + write + link for one resumable batch, but Stage 3
is intentionally **not** wired into the main `agentos-chatgpt-pipeline` yet;
that remains Stage 3.8.

## Tests

Focused tests are in:

```text
chatgpt-memory/tests/test_deep_memory_stage3.py
```

They cover queue reuse/invalidation, passage overlap/message refs, solution
confirmation gating, namespace/provenance, many-to-many projects, and
error/attempt/solution chains.

The assistant execution environment could not reach GitHub to clone and execute
the branch tests, so the next review step is a local test run in the actual
AgenticOS checkout.

## Review boundary

**Stop here. Do not begin Stage 3.5 yet.**

After the local tests pass, review schema compatibility, queue behavior,
provenance, success-confirmation rules, and relation quality. Stage 3.5 will
then add conservative deduplication, temporal state, conflicts, and review
queues.
