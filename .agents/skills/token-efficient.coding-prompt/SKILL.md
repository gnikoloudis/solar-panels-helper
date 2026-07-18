# Token-Efficient Coding Prompt

Use this skill when you need a structured, low-token prompt for any coding task.
Invoke it by describing your task — the skill formats it to minimize token waste.

---

## When to Use

- Writing new code
- Debugging or fixing a bug
- Reviewing or refactoring existing code
- Asking a technical question about the codebase

---

## Prompt Template

Fill in the brackets, delete unused fields.

```
[ROLE]: You are a [language/domain] engineer. Be concise.
[TASK]: [Single action verb + object. e.g. "Fix the off-by-one error in this loop."]
[CONTEXT]: [One sentence of relevant context. No repetition of open files.]
[FORMAT]: [e.g. "Return fixed code only." / "One sentence explanation + fix." / "Bullet list, max 3 items."]
[BUDGET]: Max [N] words. No preamble. No closing.
```

---

## Filled Examples

**Bug fix**
```
[ROLE]: You are a Python engineer. Be concise.
[TASK]: Fix the KeyError in this function.
[CONTEXT]: The dict key comes from user input and may be missing.
[FORMAT]: Return corrected code only.
[BUDGET]: Max 30 words of explanation if needed. No preamble. No closing.
```

**Code review**
```
[ROLE]: You are a senior TypeScript engineer. Be concise.
[TASK]: Review this function for correctness and performance issues.
[CONTEXT]: This runs on every keystroke in a search input.
[FORMAT]: Bullet list, max 3 issues. Each issue: problem + fix in one line.
[BUDGET]: No preamble. No closing.
```

**Architecture question**
```
[ROLE]: You are a backend systems engineer. Be concise.
[TASK]: Recommend a caching strategy for this API endpoint.
[CONTEXT]: Endpoint hits a Postgres DB, ~500 req/s, data changes every 5 minutes.
[FORMAT]: Max 3 bullet points. Lead with the recommendation.
[BUDGET]: No preamble. No closing.
```

---

## Rules This Skill Enforces

| Rule | Effect |
|---|---|
| Single scoped task | Prevents sprawling multi-part answers |
| Explicit format | Prevents narrative when code is needed |
| Word budget | Hard ceiling on response length |
| No preamble/closing | Eliminates filler tokens |
| Context by reference | Prevents re-pasting open files |
| Answer first | Inverted pyramid — conclusion before reasoning |