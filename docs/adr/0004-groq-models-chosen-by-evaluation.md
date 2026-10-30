# ADR-0004: Hosted models on Groq, with the smaller model chosen by evaluation

| | |
|---|---|
| **Date** | 2026-10-04 |
| **Status** | Accepted |

## Context

The assistant needs a language model at no cost. Groq hosts
open-weight models on a free tier with daily and per-minute limits.
Bigger models are often assumed to be better.

## Decision

Use `openai/gpt-oss-20b` on Groq by default, with
`openai/gpt-oss-120b` as a fallback when the default is rate-limited.
A rate-limited model is skipped for ten minutes.

On 6 October 2026 both were run on the same eleven test cases. The
smaller model passed 11 of 11; the larger passed 10 of 11, because it
ignored the sentinel value instruction (ADR-0002). The smaller model
stays the default.

## Consequences

- The choice rests on measurement, recorded in `evals/`.
- The assistant keeps answering when one model's allowance runs out.
- A change of model needs a new evaluation run.
