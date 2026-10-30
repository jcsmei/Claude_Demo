# ADR-0005: LangGraph for orchestration, as a routing workflow

| | |
|---|---|
| **Date** | 2026-10-04 |
| **Status** | Accepted; extended by ADR-0015 |

## Context

The flow began as a straight line: search, then answer. It grew
branches (several sources, a web fallback) and a retry loop for SQL.

## Decision

Use LangGraph to define the flow as a graph. A router node asks
the model once which source fits the message; code then follows a
fixed path. This is a routing workflow, not an agent: the model does
not choose the next step at run time.

## Consequences

- Steps, cost and guardrails are fixed and testable.
- The sidebar draws the graph from the code, so the picture cannot
  drift from it.
- Questions that need several tools combined are not supported.
  ADR-0015 adds an agent where that flexibility is needed.
