# ADR-0011: Use industry-standard terms

| | |
|---|---|
| **Date** | 2026-10-13 |
| **Status** | Accepted |

## Context

Several names in the code and documents had been coined for the
project, such as "marker" and "decision flow". Readers who know the
field would not recognise them.

## Decision

Use established terms: sentinel value, small talk, input
guardrail, routing, orchestration. When a plain explanation helps a
non-technical reader, give the standard term first and explain it
once.

## Consequences

- The project can be discussed with practitioners in their own
  vocabulary.
- New concepts are checked for an existing term before being named.
