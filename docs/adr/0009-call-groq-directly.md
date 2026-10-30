# ADR-0009: Call Groq directly, not through LangChain's ChatGroq

| | |
|---|---|
| **Date** | 2026-10-11 |
| **Status** | Accepted |

## Context

LangChain's `ChatGroq` offers a standard interface across model
providers and built-in tracing. The project has one provider.

## Decision

Keep calling the Groq client directly, in `assistant/llm.py`.
Revisit if a second model provider is added.

## Consequences

- The mechanics stay visible: roles, temperature, the fallback and
  its ten-minute skip.
- Switching providers would mean rewriting one file.
- LangChain's built-in fallback has no skip after a rate limit, so the
  project's own fallback logic would be kept if `ChatGroq` were
  adopted.
