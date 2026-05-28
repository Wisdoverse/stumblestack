---
id: 5ec275fe-5f93-4aba-8d27-9aec68125d4d
title: "OpenAI embeddings call fails when a single input exceeds the model token limit"
category: openai-api
tags:
  - openai-api
  - embeddings
  - token-limit
symptoms:
  - "maximum context length is 8192 tokens, however you requested ..."
  - "400 on embeddings input"
root_cause: "Embedding models cap input at ~8192 tokens per item. Long documents must be chunked before embedding."
fix: "Chunk text under the limit (with overlap) and embed each chunk; you can batch many chunks in one request via a list input."
verified_count: 0
_aliases:
  - "embedding input too long"
  - "text too big to embed in one request"
  - "context length exceeded on embeddings endpoint"
severity: wasted-cycles
applies_to:
  product: openai-api
  surface: embeddings
fix_code:
  language: python
  code: "client.embeddings.create(model=\"text-embedding-3-large\", input=[chunk1, chunk2])"
created: 2026-05-28
---

```python
client.embeddings.create(model="text-embedding-3-large",
                         input=[chunk1, chunk2, ...])  # list batches
```

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
