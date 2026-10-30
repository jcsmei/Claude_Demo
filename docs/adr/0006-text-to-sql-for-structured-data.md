# ADR-0006: Query structured data with SQL, not retrieval

| | |
|---|---|
| **Date** | 2026-10-04 |
| **Status** | Accepted; amended by ADR-0017 |

## Context

The assistant answers from New York City's taxi driver license
data. Retrieval finds similar text; it cannot total a column or count
rows. The source dataset also lists about 180,000 named people.

## Decision

Fetch only grouped counts from NYC Open Data, never names or
license numbers, into a temporary SQLite table. The model writes one
SQL query; code checks it: a single read-only `SELECT` that reads the
table, at most 50 rows, stopped after one million database steps. A
failed or empty query is retried once.

## Consequences

- Totals are exact, computed by the database, not the model.
- No personal data is downloaded.
- The SQL is shown under each answer, so a wrong query is visible.
