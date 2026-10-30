# ADR-0008: Guardrails enforced in code, with an input guardrail that fails open

| | |
|---|---|
| **Date** | 2026-10-05 |
| **Status** | Accepted |

## Context

The repository and the live app became public, so prompt
injection had to be defended against. A model can be asked to behave,
but not made to.

## Decision

Enforce rules in code wherever possible: instructions and outside
text in separate roles, read-only SQL, tools fixed in code, no web
search for questions naming the project's creator, asking about the
project itself, or containing contact details, no images in answers. Screen each message with a classifier (Llama Prompt
Guard 2) before the main model sees it. If the classifier is
unavailable, the message goes through.

## Consequences

- Rules hold even when the model is fooled.
- Failing open keeps the assistant usable; the other layers still
  apply.
- A novel injection can pass the classifier; it is one layer of
  several.
