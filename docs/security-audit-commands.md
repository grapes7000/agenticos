# AgenticOS Security + Build Quality Commands

Run a security/health audit:

```bash
agentos security
```

Run a deeper audit with rkhunter/chkrootkit if installed:

```bash
agentos security --deep
```

Run AgenticOS build quality checks:

```bash
agentos build-quality
```

Summarize the latest security/build reports with local Qwen/Ollama:

```bash
agentos security-summary
```

Run everything:

```bash
agentos security-full
```

From OpenClaw:

```text
/bash agentos security-full
```

Then ask:

```text
Summarize the report in plain English. Tell me what is healthy, what is risky, and the top 5 safest fixes. Do not apply fixes.
```

Reports are saved to:

- `~/vault/Agentic OS/Security Reports/`
- `~/vault/Agentic OS/Build Quality Reports/`
- `~/vault/Agentic OS/Security Summaries/`
