# MyNewApp — guided chat-first app starter

A reusable starter for building apps with ChatGPT, Ollama, Claude chat, or any other model that mainly gives you text/code in conversation.

This repo is deliberately **human-operated**: the AI helps plan, write, review, and explain code, while you control the files, terminal, tests, Git branches, commits, pushes, and pull requests.

## Core workflow

1. Define the idea.
2. Fill the planning templates with an AI after discussing the project.
3. Break v0.1 into small BUILD tasks.
4. Put exactly one task in `docs/ACTIVE_TASK.md`.
5. Create a Git branch for that task.
6. Ask an AI for one small implementation slice.
7. Paste the code into the intended repo files.
8. Run checks and tests.
9. Debug failures in a bounded way.
10. Review the diff and have an AI review/explain it.
11. Commit, push, open a PR, merge, and update project state.
12. Repeat.

The rule is: **plan broadly once; implement narrowly forever.**

## Start here

Read [`START_HERE.md`](START_HERE.md) and follow it in order. It is the tutorial for using this repository.

## Repository map

```text
.
├── README.md
├── START_HERE.md
├── AGENTS.md
├── TASKS.md
├── app/
├── docs/
│   ├── 00_IDEA.md
│   ├── 01_PROJECT_BRIEF.md
│   ├── 02_REQUIREMENTS.md
│   ├── 03_ARCHITECTURE.md
│   ├── 04_BUILD_PLAN.md
│   ├── ACTIVE_TASK.md
│   ├── CURRENT_STATE.md
│   ├── AI_HANDOFF.md
│   ├── DECISIONS.md
│   ├── BUGS.md
│   ├── TESTING.md
│   └── RELEASE_CHECKLIST.md
├── prompts/
│   ├── 01-discuss-idea.md
│   ├── 02-fill-planning-docs.md
│   ├── 03-create-build-plan.md
│   ├── 04-write-small-slice.md
│   ├── 05-review-code.md
│   ├── 06-debug-failure.md
│   └── 07-update-handoff.md
├── guides/
│   ├── WORKFLOW.md
│   ├── TERMINAL.md
│   ├── GIT.md
│   └── AI_CHAT_WORKFLOW.md
└── scripts/
    ├── preflight.sh
    └── check.sh
```

## Task types

- `BUILD-###` — add one coherent, runnable/testable capability.
- `EDIT-###` — make one small surgical change.
- `FIX-###` — repair one understood defect at its root cause.
- `CHORE-###` — bounded tooling, docs, packaging, or maintenance work.

## What this starter is not

It is not an autonomous agent controller. If you want Codex, Claude Code, OpenCode, Aider, Hermes, or another tool-using coding agent to operate the repository under an automated task/check/review controller, use `VibeLab-starter` instead.
