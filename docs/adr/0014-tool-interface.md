# ADR-0014: A small tool interface of our own

| | |
|---|---|
| **Date** | 2026-10-20 |
| **Status** | Accepted |

## Context

Adding a tool meant editing eight places. LangChain's `BaseTool`
and MCP's tool definitions share one shape: a name, a description the
model reads, and an argument schema.

## Decision

Define our own small interface, in `assistant/tools/base.py`,
with the same fields: name, description, argument schema, source
label, and `run()`. A tool returns its evidence as plain data with a
kind, and never draws it; the page has one renderer per kind. A tool
that needs several steps may bring its own subgraph. A tool that does
not fit stays outside the interface. Tools move onto it one at a
time; GitHub moved first, on 30 October 2026.

## Consequences

- Adding a tool takes one file, plus its documentation.
- Tools do not depend on LangGraph or Streamlit, so they can be tested
  alone.
- Moving to `BaseTool` later is simple, because the fields match.
