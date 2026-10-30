# ADR-0012: Version 2 answers from a fixed folder of workbooks; uploads later

| | |
|---|---|
| **Date** | 2026-10-20 |
| **Status** | Accepted |

## Context

Version 2 adds answering from tabular data. Visitor uploads were
first planned, but they bring hostile files, size limits and
separating visitors' data. An internal reporting assistant typically
reads the latest reports from a known place instead.

## Decision

Read a fixed folder, `sample_data/`, of multi-tab Excel
workbooks: the latest file of each report, by the date in its name.
Stack each workbook's tabs into one table with `_source_file` and
`_source_tab`, and add a combined view with standard column names.
Visitor uploads become an optional later phase. The sample data is
synthetic and genericised; the original generated files are not
published.

## Consequences

- Most of the value with little of the upload risk.
- Rows stay traceable to their file and tab, and an ID shared by two
  tabs cannot mix them.
- Visitors cannot try their own data until uploads are built.
