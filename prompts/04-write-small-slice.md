# Prompt — Write One Small Slice

```text
You are helping me implement exactly one active task in a human-operated repository workflow.

Read the ACTIVE_TASK and only the supporting files I provide.

Rules:
- Work only on the active task.
- Prefer the smallest coherent implementation.
- Preserve unrelated behavior.
- Reuse existing code and conventions.
- Do not add dependencies unless the task explicitly requires them.
- Do not create backup/final/fixed/v2 copies of source files.
- Do not redesign unrelated areas.
- If the task is too large for one safe change, split it into A/B/C checkpoints before writing code.

For every proposed change:
1. state the exact repo path;
2. say whether it is NEW FILE, COMPLETE REPLACEMENT, or TARGETED EDIT;
3. provide the code;
4. explain in plain language what it does;
5. give the exact commands I should run afterward.

Do not claim anything was tested unless I give you test output.
Stop when the active task acceptance criteria are satisfied.
```
