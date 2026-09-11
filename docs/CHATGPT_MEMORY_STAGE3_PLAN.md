# ChatGPT Memory Stage 3 — Deep Memory Plan

## Purpose

Stage 3 turns the already indexed and organized ChatGPT archive into durable,
source-backed memory without losing provenance or mixing identities.

Stages 0–2 already provide the inputs Stage 3 needs:

1. archive ingest, attachment recovery, and semantic embeddings;
2. identity routing (`LAKOTA`, `BROOKE`, `SHARED`, `UNKNOWN`);
3. lightweight conversation organization (summary, tags, projects, type,
   importance);
4. PCA -> UMAP -> DBSCAN semantic discovery, cluster labels, and scoped
   subclustering for oversized categories.

Stage 3 is deliberately separate from those passes. It must not re-decide
identity, rebuild embeddings, or use a broad one-shot prompt over every chat.

## Goals

Stage 3 should produce durable memory for things that remain useful after the
original conversation is over:

- project and system state;
- architecture and implementation decisions;
- reasons behind decisions;
- confirmed working commands and procedures;
- errors and known issues;
- failed approaches and why they failed;
- configuration, paths, services, versions, and settings;
- reusable workflows and lessons learned;
- durable facts and preferences;
- explicit unresolved questions or TODOs.

Every stored claim must be traceable to source evidence.

## Non-goals

Stage 3 must not:

- treat assistant suggestions as facts without user confirmation;
- collapse historical state into current state without evidence;
- silently merge Brooke and Lakota memory;
- promote raw model output directly into Hermes or another persistent agent
  memory store;
- discard contradictory evidence;
- depend on cluster labels being perfect;
- require the original export to be modified.

## Inputs

Canonical input remains:

```text
chatgpt-memory/data/memory.sqlite3
```

Stage 3 consumes, when available:

- `conversations` — source transcript and dates;
- `chat_chunks` — semantic chunks and embeddings;
- `identity_classifications` — identity namespace;
- `conversation_organizations` — summary, tags, projects, type, importance;
- `semantic_cluster_runs`, `semantic_clusters`, `conversation_reductions` —
  discovered semantic neighborhoods;
- attachment provenance and extracted attachment text;
- existing legacy `deep_facts` / `project_facts` as migration inputs only;
- `projects`, `conversation_projects`, and `knowledge_items` from
  `knowledge_index.py`.

Identity and organization are upstream decisions. Stage 3 reads them; it does
not overwrite them.

## Memory namespaces

Every deep-memory item belongs to one identity namespace:

```text
lakota
brooke
shared
unknown
```

Cross-identity consolidation is forbidden by default. A `SHARED` source may be
linked to both people where appropriate, but a Brooke item must not silently
become Lakota memory and vice versa.

Project membership remains many-to-many: one conversation and one extracted
item may relate to multiple projects.

## Stage 3A — Build a resumable extraction queue

Create a queue from organized conversations rather than blindly processing in
conversation order.

Priority signals:

- importance 5 before 4 before 3;
- explicit project membership;
- development, troubleshooting, setup/configuration, and planning conversations;
- conversations near the center of coherent semantic clusters;
- cluster representatives that cover otherwise underrepresented topics;
- recent conversations when determining current state;
- conversations referenced by multiple attachments or related project facts.

Low-importance/general conversations are not deleted or permanently excluded;
they are simply processed after higher-value material.

The queue must be resumable and content-hash aware. If the source conversation
has not changed, a successful extraction is reused.

### Proposed tables

```text
deep_memory_runs
  run_id
  model
  config_json
  created_at

deep_memory_extractions
  conversation_id
  passage_index
  passage_hash
  run_id
  state
  attempts
  last_error
  completed_at
```

## Stage 3B — Passage-level extraction

Do not ask one prompt to summarize an entire long conversation. Split the
conversation into bounded passages that preserve turn boundaries, with small
overlap where needed.

For each passage, request atomic items using a strict structured schema.

### Item categories

```text
error
failed_approach
confirmed_solution
decision
decision_reason
configuration
workflow
project_status
system_state
lesson
durable_fact
preference
unresolved
```

Each item should include:

```json
{
  "category": "confirmed_solution",
  "statement": "...",
  "projects": ["AgenticOS"],
  "confidence": 0.94,
  "temporal_status": "current|historical|superseded|unknown",
  "evidence": "short source-supported excerpt/paraphrase",
  "success_evidence": "what showed that the fix actually worked",
  "related_item_hint": "optional local relationship hint"
}
```

Rules:

- a solution is `confirmed_solution` only when later source evidence indicates it
  worked;
- an attempted command with no confirmed outcome is not a solution;
- failed attempts are valuable and should be stored independently;
- exact error strings, paths, versions, and commands should be retained when
  they materially identify the issue;
- current/historical/superseded status must be explicit rather than inferred
  away during consolidation.

## Stage 3C — Normalize and write source-backed knowledge

Reuse the existing `projects`, `conversation_projects`, and `knowledge_items`
foundation from `knowledge_index.py`.

Extend it non-destructively with evidence and relationship tables rather than
creating another competing project index.

### Proposed additions

```text
knowledge_evidence
  knowledge_item_id
  conversation_id
  message_or_passage_ref
  evidence_text
  source_date

knowledge_relations
  source_item_id
  relation
  target_item_id

knowledge_conflicts
  item_a_id
  item_b_id
  reason
  resolution_status

knowledge_overrides
  stable_key
  action
  value_json
  reason
  created_at
```

Useful relationships include:

```text
error -> failed_approach
error -> confirmed_solution
decision -> decision_reason
configuration -> supersedes -> configuration
project_status -> supersedes -> project_status
item -> related_to -> item
```

The original source-backed items remain immutable evidence. Consolidation may
link or supersede them, but must not erase the original claim.

## Stage 3D — Deduplicate and link related facts

Deduplication should be conservative.

Two items may be grouped when their meaning, affected component/project, and
context agree. Similar wording alone is insufficient.

For errors, normalize a signature from fields such as:

```text
project/component + symptom/error string + environment
```

Then build chains such as:

```text
error
  -> failed attempt 1
  -> failed attempt 2
  -> confirmed solution
```

Multiple source conversations can support the same durable conclusion. Keep all
source links even after consolidation.

## Stage 3E — Resolve temporal state and contradictions

Current state cannot be chosen solely by newest timestamp.

For conflicting claims:

1. prefer explicit statements that something changed or was fixed;
2. use chronology as supporting evidence, not the only rule;
3. retain older values as historical/superseded;
4. if evidence is insufficient, create a conflict/review item instead of
   guessing.

Examples:

```text
old: SSH port is 22
new: SSH moved to port 2222
=> 22 = superseded, 2222 = current
```

```text
chat A: Open WebUI is broken
chat B: user says it works now
=> broken state = historical, working state = current
```

## Stage 3F — Cluster/project consolidation

Semantic clusters are context, not truth. Use them to gather related evidence
and to avoid analyzing project state conversation-by-conversation in isolation.

For each project and useful semantic cluster:

1. collect source-backed knowledge items;
2. identify repeated facts and relationships;
3. identify contradictions and state transitions;
4. produce a compact current-state snapshot;
5. keep links back to all supporting items.

This is where the PCA/UMAP/DBSCAN work becomes useful to deep memory: clusters
help discover families of conversations that should be consolidated together,
even when the Stage-2 category or explicit project label is broad.

## Stage 3G — Render durable project memory

Generated Markdown is a view of SQLite, not a second source of truth.

Target layout:

```text
chatgpt-memory/memory/
  lakota/
    projects/
      agenticos/
        README.md
        CURRENT_STATE.md
        DECISIONS.md
        CONFIGURATION.md
        ERRORS_AND_FIXES.md
        WORKFLOWS.md
        HISTORY.md
  brooke/
    projects/
  shared/
    projects/
```

Project documents should contain concise statements with provenance references,
not copied conversation dumps.

## Stage 3H — Review queue and durable corrections

Send these to review instead of guessing:

- conflicting current-state claims;
- project assignment with low confidence;
- solution without explicit success evidence;
- ambiguous identity namespace;
- aggressive deduplication candidates;
- uncertain supersession relationships.

A user correction must be stored as a durable override so a later rebuild does
not undo it.

## Stage 3I — Search integration

`agentos-memory-search` should eventually search both:

1. consolidated durable knowledge for concise answers;
2. raw semantic archive chunks for recall and source inspection.

Preferred retrieval order:

```text
current durable project memory
-> source-backed atomic knowledge items
-> semantic conversation/attachment chunks
-> original transcript or recovered asset
```

## Implementation slices

### 3.1 — Schema and queue

- add Stage-3 run/extraction state;
- compute priority from Stage-2 metadata and cluster membership;
- add `status` and resumable queue commands;
- tests for idempotency and changed-conversation invalidation.

### 3.2 — Structured passage extractor

- bounded turn-aware passage construction;
- strict JSON schema;
- retry/timeout handling;
- atomic categories and evidence rules;
- no consolidation yet.

### 3.3 — Project routing and knowledge writer

- consume Stage-2 projects plus project hints from extraction;
- many-to-many conversation/project and item/project links;
- write source-backed `knowledge_items`;
- preserve namespace and provenance.

### 3.4 — Relations, success confirmation, and error chains

- link errors, attempts, and confirmed fixes;
- prevent unconfirmed suggestions from becoming solutions;
- add knowledge relationships and evidence records.

### 3.5 — Deduplication, temporal state, and conflicts

- conservative semantic grouping;
- current/historical/superseded logic;
- conflict and review queues;
- durable user overrides.

### 3.6 — Project/cluster consolidation

- use semantic cluster membership as additional grouping context;
- consolidate related items into current project/system state;
- retain all backing evidence.

### 3.7 — Markdown and search integration

- render per-namespace project dossiers;
- update hybrid search to prefer durable knowledge while retaining raw recall;
- add source navigation from rendered facts.

### 3.8 — Pipeline integration

Add Stage 3 to `bin/agentos-chatgpt-pipeline` only after the preceding slices are
stable. The runner should resume Stage 3 just as it currently resumes identity,
organization, and semantic clustering.

## Acceptance criteria

Stage 3 is complete when:

- every durable claim has at least one source conversation/evidence reference;
- identities/namespaces are never silently mixed;
- successful fixes require success evidence;
- failed approaches are searchable separately from confirmed solutions;
- one conversation/item can belong to multiple projects;
- current and historical state can coexist;
- conflicts are preserved or queued rather than silently overwritten;
- reruns are idempotent for unchanged conversations;
- changed source conversations invalidate only affected derived memory;
- cluster context is used for consolidation but never treated as factual proof;
- generated Markdown can be rebuilt entirely from SQLite;
- raw transcripts and exports remain unmodified.

## First implementation target

Start with **3.1 — Schema and queue**. Do not begin the extractor until the queue,
resume behavior, invalidation rules, and tests are stable.
