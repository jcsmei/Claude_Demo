# Architecture decision records

Each significant decision about the assistant's architecture, with
its context and consequences. The format is the one Michael Nygard
popularised. A record is not edited once accepted: a later decision
marks it as amended or superseded instead. Decisions made before
30 October 2026 were recorded retrospectively, dated when they were
made.

| Record | Decision | Date | Status |
|---|---|---|---|
| [ADR-0001](0001-record-architecture-decisions.md) | Record architecture decisions | 2026-10-30 | Accepted |
| [ADR-0002](0002-answer-only-from-sources.md) | Answer only from sources, and abstain with a sentinel value | 2026-10-04 | Accepted |
| [ADR-0003](0003-embedded-vector-store.md) | Chroma as an embedded vector store, rebuilt from the knowledge base | 2026-10-04 | Accepted |
| [ADR-0004](0004-groq-models-chosen-by-evaluation.md) | Hosted models on Groq, with the smaller model chosen by evaluation | 2026-10-04 | Accepted |
| [ADR-0005](0005-langgraph-orchestration.md) | LangGraph for orchestration, as a routing workflow | 2026-10-04 | Accepted; extended by ADR-0015 |
| [ADR-0006](0006-text-to-sql-for-structured-data.md) | Query structured data with SQL, not retrieval | 2026-10-04 | Accepted |
| [ADR-0007](0007-mcp-server-and-client.md) | MCP as both server and client | 2026-10-04 | Accepted |
| [ADR-0008](0008-guardrails-in-code.md) | Guardrails enforced in code, with an input guardrail that fails open | 2026-10-05 | Accepted |
| [ADR-0009](0009-call-groq-directly.md) | Call Groq directly, not through LangChain's ChatGroq | 2026-10-11 | Accepted |
| [ADR-0010](0010-package-layout.md) | One package, two entry points | 2026-10-11 | Accepted |
| [ADR-0011](0011-industry-standard-terms.md) | Use industry-standard terms | 2026-10-13 | Accepted |
| [ADR-0012](0012-workbook-data-source.md) | Version 2 answers from a fixed folder of workbooks; uploads later | 2026-10-20 | Accepted |
| [ADR-0013](0013-business-definitions.md) | Business definitions for the workbook data | 2026-10-20 | Accepted |
| [ADR-0014](0014-tool-interface.md) | A small tool interface of our own | 2026-10-20 | Accepted |
| [ADR-0015](0015-hybrid-workflow-and-agent.md) | Hybrid: a deterministic workflow, with an agent for data analysis | 2026-10-30 | Accepted |
| [ADR-0016](0016-observability-and-system-of-record.md) | Observability and the system of record | 2026-10-15 | Proposed |

**Statuses.** Proposed: under discussion. Accepted: in force.
Amended: partly changed by a later record. Superseded: replaced.

**Where else to look.** [ARCHITECTURE.md](../../ARCHITECTURE.md)
describes the system as it is now. The [design documents](../design/)
are dated snapshots of what was planned.

**Adding a record.** Copy the newest file, take the next number, and
fill in the date, status, context, decision and consequences.
