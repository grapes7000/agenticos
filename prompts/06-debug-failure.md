# Prompt — Debug One Failure

```text
Help me debug this failure without broad rewrites.

I will provide:
- the ACTIVE_TASK;
- the exact command I ran;
- the exact error/output;
- only the relevant code/files.

First identify the most likely root cause from the evidence. Then propose the smallest repair that addresses that root cause.

Rules:
- do not make random speculative edits;
- do not disable tests, type checks, validation, or security controls to make the command pass;
- preserve unrelated behavior;
- tell me exactly which file/path changes;
- explain why the fix should work;
- give the exact command to rerun.

If two materially different repair attempts have already failed, stop and reassess assumptions/root cause before suggesting a third edit.
```
