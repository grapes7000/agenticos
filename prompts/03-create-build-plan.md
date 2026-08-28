# Prompt — Create the Build Plan

```text
Read the project brief, requirements, architecture, testing plan, and durable decisions I provide.

Do not implement code.

Break the target release into the smallest sensible sequence of BUILD tasks. Each task must:
- produce one coherent capability;
- leave the app runnable or meaningfully testable when possible;
- list dependencies;
- list likely files without pretending certainty where the repo does not exist yet;
- contain observable acceptance criteria;
- contain exact verification commands when known;
- avoid bundling unrelated cleanup or future ideas.

Use BUILD for capabilities, EDIT for surgical changes, FIX for root-cause repairs, and CHORE for bounded tooling/docs/packaging work.

Return complete replacement content for:
1. docs/04_BUILD_PLAN.md
2. TASKS.md

If any architectural decision is still missing and materially changes the task order, identify it instead of guessing.
```
