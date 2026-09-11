# Prompt — Fill Planning Documents

Paste the relevant templates plus your completed idea discussion into the AI chat, then use:

```text
Using only the decisions we already made, fill these project templates cleanly:
- docs/00_IDEA.md
- docs/01_PROJECT_BRIEF.md
- docs/02_REQUIREMENTS.md

Do not write implementation code.
Do not silently invent product requirements.
If a missing decision blocks a useful answer, ask me before filling it.
For each file, return the COMPLETE replacement Markdown content under a heading containing the exact repo path.
Keep v0.1 intentionally small and move optional ideas to out-of-scope/deferred sections.
```
