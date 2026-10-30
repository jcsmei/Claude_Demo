# ADR-0010: One package, two entry points

| | |
|---|---|
| **Date** | 2026-10-11 |
| **Status** | Accepted |

## Context

The code was a flat set of modules at the top of the repository.
More features were planned.

## Decision

Put the assistant's modules in a package, `assistant/`. Keep the
two entry points, `app.py` and `mcp_server.py`, at the top, where
Streamlit and MCP clients start them. Entry points import the package;
the package never imports them.

## Consequences

- New modules have a place to go.
- The chat page and the MCP server are two thin interfaces over one
  core.
