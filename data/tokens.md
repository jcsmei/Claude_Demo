# Tokens, limits and running costs

## How many tokens does each kind of answer use?

These are estimates, not exact measurements. An answer from the
documents takes two model calls and roughly 2,000 to 3,000 tokens,
most of it the five retrieved passages. An answer from GitHub takes
two calls and somewhat fewer tokens. An answer from the taxi data
takes three calls: choose the tool, write the query, explain the
result. A web answer is the most expensive: three calls and roughly
1,000 tokens more than a documents answer, plus one Tavily search
credit. Every message also gets one small screening call to a separate
classifier model with its own allowance. Token use is the main running
cost, so it is tracked and kept low on purpose.

## Is there a rate limit on questions?

Yes, three limits apply. Each visit is limited to 20 questions. The
project's Groq account, on the free tier, allows each model 8,000
tokens per minute and 200,000 tokens per day. A chat message uses
roughly 2,500 to 4,000 tokens across two or three model calls, so the
main model can answer about 50 to 80 messages per day across all
visitors. When the main model reaches a limit, the bot switches to a
second model. Only if both are limited does the page say which limit
was reached and when to try again.

## What happens when the tokens run out and the model's allowance is used up?

Groq counts its limits separately for each model. When the main model,
openai/gpt-oss-20b, is rate limited, the bot sends the same question
to a second model on the same account, openai/gpt-oss-120b, so
visitors still get an answer. The main model is then skipped for ten
minutes, so that later questions do not each wait on a request that
would be refused. Every switch is written to the log. If both models
are rate limited, the page says so. This was chosen over a mode that
only shows search results, because the bot should stay able to answer.
