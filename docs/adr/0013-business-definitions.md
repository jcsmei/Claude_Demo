# ADR-0013: Business definitions for the workbook data

| | |
|---|---|
| **Date** | 2026-10-20 |
| **Status** | Accepted |

## Context

The workbook data allows more than one correct-sounding answer to
the core questions. On Reddit, 29 creatives are live across 13
campaigns. On Twitter Paid, 24 creatives are not live and 8 have
status Unknown.

## Decision

The creative is the unit counted. "Not live" means status
`Not Live` only; Unknown is always reported separately. A question
about campaigns is answered with both numbers. Platform names are
mapped from common synonyms to tab names. The full list is in
[the version 2 design](../design/2026-10-11-version-2.md), section 4.4.

## Consequences

- One agreed meaning per term: a small semantic layer.
- Answers state their basis, so a reader can tell 29 from 13.
