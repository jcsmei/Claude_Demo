# ADR-0001: Record architecture decisions

| | |
|---|---|
| **Date** | 2026-10-30 |
| **Status** | Accepted |

## Context

The project's decisions were spread across design documents,
commit messages and conversation. A reader could see what was built,
but not easily why, or what was considered and set aside.

## Decision

Record each significant architecture decision as a short,
numbered record in `docs/adr/`, in the format Michael Nygard
popularised: context, decision, consequences. A record is not edited
once accepted; a later decision marks it as superseded instead.

Decisions made before 30 October 2026 are recorded retrospectively,
dated when they were made.

## Consequences

- Anyone can follow how the design changed, and why.
- Design documents in `docs/design/` are kept as dated snapshots;
  `ARCHITECTURE.md` describes the system as it is now.
- Each significant decision needs a record written when it is made.
