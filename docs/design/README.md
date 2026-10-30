# Design documents

Each design document is a dated snapshot of what was planned at the
time. When a design changes substantially, a new document is added
and the old one is kept, marked as superseded, so the reasoning can
be followed over time.

| Document | Date | Status | What it covers |
|---|---|---|---|
| [Version 2](2026-10-11-version-2.md) | 11 October 2026, phase 3 revised 20 October | Current, except phase 3 | Workbook data, a system of record, the tool interface, build order and estimate |

**What changed, and why**

| Date | Change | Recorded in |
|---|---|---|
| 20 October 2026 | Phase 3 answers from a fixed folder of workbooks instead of visitor uploads, which become optional | [ADR-0012](../adr/0012-workbook-data-source.md) |
| 30 October 2026 | Workbook questions go to an agent with a step limit; everything else stays a deterministic workflow. A revised design will follow. | [ADR-0015](../adr/0015-hybrid-workflow-and-agent.md) |

**Where else to look.** [ARCHITECTURE.md](../../ARCHITECTURE.md)
describes the system as it is now. The
[architecture decision records](../adr/) give the reason for each
significant decision.
