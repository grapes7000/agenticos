# Prompt — Review and Explain the Code

```text
Review this change against the ACTIVE_TASK and the relevant project docs/files I provide.

Check:
- whether the acceptance criteria are actually met;
- correctness and likely regressions;
- unnecessary complexity;
- duplicated logic;
- architecture/convention fit;
- accidental scope creep;
- security/privacy concerns when relevant;
- missing tests or verification;
- misleading comments or dead code.

Separate findings into:
1. MUST FIX before commit
2. SHOULD FIX if small and directly relevant
3. OPTIONAL / future work

Then explain the changed code to me in plain language, including the important functions/classes/data flow and why the implementation works.

Do not rewrite the whole project. Recommend the smallest fixes needed. If the change looks good, say so clearly and tell me what remains unverified.
```
