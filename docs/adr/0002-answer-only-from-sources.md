# ADR-0002: Answer only from sources, and abstain with a sentinel value

| | |
|---|---|
| **Date** | 2026-10-04 |
| **Status** | Accepted |

## Context

An assistant that answers from the model's own memory can state
things that are not true. The assistant needed a reliable way to
refuse when its documents do not hold the answer.

A cutoff on retrieval distance was considered and measured: an
unanswerable question scored closer (1.05) than an answerable one
(1.65), so no cutoff could separate them.

## Decision

The model answers only from the passages, rows or results it is
given. When they do not hold the answer, it replies with a sentinel
value, a fixed word reserved for this purpose, and code writes the
refusal.

## Consequences

- The program always knows whether a question was answered.
- Refusals are worded consistently.
- The approach depends on the model following the instruction; the
  model evaluation tests that (ADR-0004).
