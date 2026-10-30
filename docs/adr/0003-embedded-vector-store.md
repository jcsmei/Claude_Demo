# ADR-0003: Chroma as an embedded vector store, rebuilt from the knowledge base

| | |
|---|---|
| **Date** | 2026-10-04 |
| **Status** | Accepted |

## Context

The knowledge base is ten Markdown documents. Retrieval needs a
vector store. The host's disk is wiped on restart.

## Decision

Use Chroma inside the app's process, with its default embedding
model (all-MiniLM-L6-v2). The index is derived from `data/` and
rebuilt when a document changes, detected by a hash of the documents.
Documents are split into chunks of about 500 characters, starting a
new chunk at each heading; the five closest chunks are retrieved. The
chunking was refined after early retrieval misses.

## Consequences

- Nothing extra to run or pay for.
- The index can always be rebuilt; it is never the source of truth.
- Adding or lengthening a document can push a passage out of the top
  five, so a retrieval benchmark guards against regressions.
