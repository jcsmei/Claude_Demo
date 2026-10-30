# ADR-0016: Observability and the system of record

| | |
|---|---|
| **Date** | 2026-10-15 |
| **Status** | Proposed |

## Context

Version 2 planned a Postgres log of requests and feedback. Tracing
was discussed: LangSmith, or OpenTelemetry with traces stored as JSON
Lines and queried with DuckDB. The live app's disk is wiped on
restart, so anything kept must be stored elsewhere. Traces sent to a
hosted service include visitors' questions.

## Decision

Not yet decided. Three options:

1. LangSmith for traces and feedback; DuckDB only for the workbooks.
2. DuckDB throughout, made durable.
3. Postgres for the record, with OpenTelemetry for traces.

## Consequences

- Phases 4 and 5 of version 2 wait on this decision.
- Whichever is chosen, the request log records what happened, not
  what visitors typed, unless a retention policy is agreed.
