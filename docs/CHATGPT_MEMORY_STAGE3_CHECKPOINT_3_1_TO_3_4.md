# Stage 3 Review Checkpoint — 3.1 through 3.4

This checkpoint records the implementation boundary requested before Stage 3.5.

## Implemented

- 3.1 — schema, priority queue, resume, content-aware invalidation
- 3.2 — bounded passage extraction with strict JSON and message-level provenance
- 3.3 — project routing, namespace preservation, source-backed knowledge writing
- 3.4 — assistant-only blocking, confirmed-solution gating, evidence records, and relations

## Primary code

```text
chatgpt-memory/src/deep_memory.py
bin/agentos-chatgpt-deep-memory
```

## Tests

```text
chatgpt-memory/tests/test_deep_memory_stage3.py
chatgpt-memory/tests/test_deep_memory_queue.py
```

Run locally before Stage 3.5:

```bash
cd ~/AgenticOS
python3 -m unittest \
  chatgpt-memory/tests/test_deep_memory_stage3.py \
  chatgpt-memory/tests/test_deep_memory_queue.py -v
```

Then initialize/rebuild the queue without making model calls:

```bash
python3 chatgpt-memory/src/deep_memory.py queue --model qwen2.5:7b-instruct
python3 chatgpt-memory/src/deep_memory.py status
```

Do not run a large extraction batch until the queue/status output has been reviewed.

## Review questions

1. Does queue priority put high-importance project/technical conversations first?
2. Does rerunning `queue` reuse unchanged completed passages?
3. Does a changed conversation invalidate only its affected Stage-3 work?
4. Are message refs and evidence retained clearly enough for source inspection?
5. Are assistant-only claims blocked from durable knowledge?
6. Are confirmed solutions supported by user-authored success evidence?
7. Does one item correctly retain multiple project memberships?
8. Are error -> failed approach -> confirmed solution chains useful and conservative?

## Stop boundary

Stage 3.5 (deduplication, temporal state resolution, conflicts, and review queues)
is intentionally not implemented in this checkpoint.
