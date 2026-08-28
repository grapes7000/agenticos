# START HERE

AgenticOS uses a checkpoint workflow designed around small local-AI coding slices and human-controlled testing/Git.

## The development rule

**Qwen writes tiny tasks. Complete a whole checkpoint. Then ChatGPT reviews and explains the checkpoint before the next one begins.**

Qwen is being used here as proof of working local code generation, not as a repository agent. You should not need to upload the repo, planning docs, or source tree to it for these early tasks. Ask ChatGPT for a self-contained Qwen prompt for the next task; that prompt should include the exact interfaces and context Qwen needs.

## Initial setup

Clone and enter the repo:

```bash
git clone <AGENTICOS-REPO-URL>
cd agenticos
```

Read:

- `README.md`
- `docs/01_PROJECT_BRIEF.md`
- `docs/03_ARCHITECTURE.md`
- `TASKS.md`

Checkpoint 1 is already selected. `docs/ACTIVE_TASK.md` points at the first slice.

## For each lettered task

### 1. Ask ChatGPT for the Qwen prompt

Example request:

```text
Give me the self-contained Qwen prompt for BUILD-001A.
```

The prompt should tell Qwen:

- exactly what to implement;
- exact file path(s);
- required public interfaces;
- allowed dependencies;
- behaviors and edge cases;
- what not to implement yet;
- tests or proof command expected;
- delivery format so code can be copied directly.

Do not make Qwen infer the architecture from missing repository files.

### 2. Give only that prompt to Qwen

Qwen should normally return one complete small file or a very small set of files. It does not need repo access for the first five checkpoints.

If Qwen tries to expand scope, ignore the extra work and keep only the requested slice.

### 3. Paste the code into the exact path

Do not create alternate copies such as `network_new.py`, `final.py`, or `fixed2.py`.

### 4. Run the task-specific proof

Use the command included in the prompt. Typical commands will eventually include:

```bash
python -m pytest -q
agent --help
agent status
agent network
```

Keep exact failures. Do not paraphrase terminal errors before asking for help.

### 5. Fix only that task if needed

For a straightforward bug, give Qwen the exact failure plus the current relevant code, or ask ChatGPT for a bounded repair prompt.

Do not move to the next lettered task until the current slice's proof passes.

### 6. Commit the small slice

Recommended flow:

```bash
git status
git diff
python -m pytest -q
git add <intended-files>
git diff --cached
git commit -m "build: complete BUILD-001A"
```

You may keep all tasks for one checkpoint on the same checkpoint branch if that is easier to follow.

## Recommended branch model

One branch per checkpoint is less annoying than one branch per tiny Qwen slice:

```bash
git switch main
git pull --ff-only
git switch -c build/checkpoint-1-core
```

Commit each lettered task separately so regressions are easy to understand.

## When the checkpoint is complete

Do not start the next checkpoint yet.

Run the checkpoint proof and gather:

```bash
git status
git diff main...HEAD
python -m pytest -q
```

plus the real user-facing command for that checkpoint, such as:

```bash
agent status
```

Then ask ChatGPT to review the **completed checkpoint**. ChatGPT should:

1. review correctness and architecture;
2. catch bugs and brittle parsing;
3. compare the implementation with checkpoint acceptance criteria;
4. explain the important Python/Linux code in plain language;
5. identify only necessary fixes;
6. tell you when the checkpoint is safe to merge and advance.

After fixes pass, merge the checkpoint and update project state.

## Checkpoint order

```text
1  core + agent status
2  network + VPN/Mullvad intelligence
3  local system health
4  Docker/self-hosting diagnostics
5  Ollama/local-AI diagnostics
6  development environment
7  homelab
8  explicit actions
9  guided troubleshooting / optional AI explanation
10 configuration + JSON/completion
11 CLI v1.0 hardening
→ TUI / Qt GUI
→ daily-use discovery loop
```

## Important boundaries for Checkpoints 1–5

- checks are read-only;
- no `sudo`;
- no automatic fixes;
- no service/container restarts;
- no package installation;
- no daemon;
- no TUI/Qt yet;
- no LLM deciding factual system state;
- no giant plugin/framework abstraction.

## The loop to remember

```text
pick lettered task
→ get self-contained Qwen prompt
→ Qwen writes small slice
→ paste exact file(s)
→ run proof/tests
→ bounded fix if necessary
→ commit slice
→ next lettered task
→ finish checkpoint
→ ChatGPT reviews + teaches checkpoint
→ fix/check/merge
→ next checkpoint
```
