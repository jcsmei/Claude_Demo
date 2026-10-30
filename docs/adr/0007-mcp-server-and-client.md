# ADR-0007: MCP as both server and client

| | |
|---|---|
| **Date** | 2026-10-04 |
| **Status** | Accepted |

## Context

Other AI assistants, such as Claude Code, could use the project's
tools. Separately, the assistant needed web search without writing a
search integration.

## Decision

Expose four tools through an MCP server (`mcp_server.py`):
search documents, ask documents, recent commits and query license
data. Separately, act as an MCP client of Tavily's hosted MCP server,
calling only its search tool. The two are separate one-way
connections, not one two-way exchange.

## Consequences

- The same core serves the chat page and other AI assistants.
- Web search runs only when the documents do not cover a question,
  and each web answer is labelled as not from the official documents.
- Only Tavily's plain search tool is used; its other tools can spend
  many credits per call.
