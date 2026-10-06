# How the language models were evaluated

## How were the models evaluated and compared?

The two candidate models were compared with a fixed evaluation. Eleven
test cases were written, each with its pass criteria decided before
the run: the tool that should answer, whether the bot should answer,
refuse or ask what was meant, and a fact the answer must contain. Both
models were put through the whole decision flow on the same questions,
the same knowledge base and the same prompts, so the model was the
only thing that differed.

## What did the model evaluation test?

The eleven cases cover six kinds of behaviour. Facts from the
knowledge base, such as the project's codename. A question that must
be refused, the capital of France. A greeting, which should not be
answered as a question. A follow-up that only makes sense with the
conversation. Routing to the right tool, GitHub. And writing SQL that
returns the exact number, checked against a figure computed separately
from the data.

## What were the results of the model evaluation?

The smaller model, openai/gpt-oss-20b, passed 11 of 11 cases. The
larger model, openai/gpt-oss-120b, passed 10 of 11. Both got every
fact, refusal, follow-up, routing and SQL case right. The larger model
failed the greeting: told to reply with a fixed marker, it wrote its
own reply instead. Token use was almost the same, about 14,000 each.
Speed could not be compared fairly, because some answers waited on the
rate limit.

## Why is the smaller model the default and not the larger one?

Because the evaluation gave no reason to prefer the larger one. The
two tied on accuracy, and the smaller model followed the control
instructions more reliably, which the refusals and guardrails depend
on. It also costs several times less per token on a paid plan. The
creator first proposed making the larger model the default; the
evaluation was run to decide, and the result was to keep the smaller
one and hold the larger in reserve. Choosing the smallest model that
passes is called right-sizing.

## What does the model evaluation not prove?

It is a small evaluation: eleven cases, one run each. That is enough
to show there is no evidence for switching models, but not enough to
say the larger model is worse in general. It checks facts and
behaviour with automatic rules, not tone or clarity, which were judged
by reading the answers. And the first run's own check had a bug: it
failed two correct answers because of an unusual space character,
which was found by reading the output.

## What is the difference between automated and human evaluation?

Automated evaluation checks answers with rules: is the right number
present, was the right tool used, was the question refused. It is
repeatable and cheap, but it only measures what has a definite right
answer. Human evaluation means a person reads the answers and judges
qualities such as clarity and tone. What makes either one rigorous is
the same: a fixed set of questions, criteria decided in advance, and
recorded results. This project uses both.

## How can the model evaluation be run again?

The evaluation is a script in the repository, in the folder named
evals. Running python -m evals.compare_models repeats it on both
models and saves the results to evals/results.json. It makes real
model calls, about 14,000 tokens per model, so it is run by hand and
is not part of the automated tests. Its scoring rules are covered by
the automated tests, so that the checker itself cannot silently be
wrong.
