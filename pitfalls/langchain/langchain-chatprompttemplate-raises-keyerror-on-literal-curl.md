---
id: 451f91b7-28df-4de2-9367-f987f53d250c
title: "LangChain ChatPromptTemplate raises KeyError on literal curly braces in the template"
category: langchain
tags:
  - langchain
  - prompts
  - templating
symptoms:
  - "KeyError on a brace-wrapped token that was meant to be literal"
  - "ValueError: Single '{' encountered in format string"
root_cause: "LangChain prompt templates use `{var}` for variables. Literal braces — JSON examples, code with `{}` — are parsed as variables and fail."
fix: "Escape literal braces by doubling them: `{{` and `}}`."
verified_count: 0
created: 2026-05-28
---

## Wrong

```python
ChatPromptTemplate.from_template('Return {"ok": true}')
```

## Correct

```python
ChatPromptTemplate.from_template('Return {{"ok": true}}')
```

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
