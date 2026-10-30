# ADR-0015: Hybrid: a deterministic workflow, with an agent for data analysis

| | |
|---|---|
| **Date** | 2026-10-30 |
| **Status** | Accepted |

## Context

LangGraph's `ToolNode` and agent loops let the model call tools
repeatedly and decide each next step. That suits open-ended analysis,
but makes cost, step count and guardrails depend on the model.
Anthropic's guide "Building effective agents" distinguishes workflows
from agents and advises the simplest that does the job.

## Decision

Keep governance deterministic, in code: the input guardrail, small
talk, routing, privacy rules and the web search order. Answer workbook
questions with an agent node that has a step limit and the workbook
tools: count, show, describe, and text-to-SQL as a last resort.

## Consequences

- Cost and guardrails stay fixed for most questions.
- Multi-step analysis, such as "which platform with the most spend has
  the fewest live creatives?", becomes possible.
- The agent needs function calling, to be tested on the chosen model
  before phase 3.
- Evaluation must check the steps the agent took, not only its
  answer.
