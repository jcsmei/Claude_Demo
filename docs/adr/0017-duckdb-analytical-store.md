# ADR-0017: DuckDB, in memory, as the analytical store

| | |
|---|---|
| **Date** | 2026-10-11 |
| **Status** | Accepted; amends ADR-0006 |

## Context

Version 2 answers questions from tabular data: three multi-tab
workbooks (ADR-0012), and the NYC license counts already queried with
SQL in a temporary SQLite table (ADR-0006). The questions are
analytical: counts, totals and comparisons across tabs and files. The
host wipes local files on restart. DuckDB's SQL can read files and
reach the network, which model-written SQL must never do.

## Decision

Use DuckDB, in memory, for all tabular data, so there is one SQL
dialect and one set of safety rules. The workbooks are loaded at
startup with openpyxl, reading values only, and each workbook's tabs
are stacked into one table with `_source_file` and `_source_tab`. A
view, `creatives`, gives the three workbooks one standard set of
column names.

Before any query runs, file and network access are switched off and
the configuration is locked, so no statement can switch them back on.
Each query runs inside a transaction that is always rolled back, so
nothing it changes is kept. Queries return at most 50 rows and are
stopped after 5 seconds.

The NYC dataset moves from SQLite to DuckDB on 30 October 2026.

## Consequences

- Analytical queries run in the app's own process, with nothing extra
  to host or pay for.
- Nothing in DuckDB survives a restart; it is rebuilt from the
  workbooks and from NYC Open Data, which are the sources of truth.
- A query is stopped by time, not by counting database steps as
  SQLite allowed.
- The record of requests and feedback does not live in this database
  (ADR-0016).
