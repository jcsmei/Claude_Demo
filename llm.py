"""Send a question to a Groq-hosted language model and return its reply."""

import logging
import os
import time

import groq
from dotenv import load_dotenv
from groq import Groq

# Read GROQ_API_KEY (and optionally the model names) from the .env file.
load_dotenv()

DEFAULT_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
# Groq's limits are counted per model, so when one model's allowance
# runs out another can still answer.  Set to an empty value to disable.
FALLBACK_MODEL = os.getenv("GROQ_FALLBACK_MODEL", "openai/gpt-oss-120b")
# After a model is rate limited it is skipped for this long, so that
# later questions do not each wait on a request that will be refused.
SKIP_SECONDS = 600

logger = logging.getLogger("rag_demo.llm")
_skip_until = {}


def reset_fallback():
    """Forget which models were rate limited."""
    _skip_until.clear()


def ask(question, client=None, model=DEFAULT_MODEL, temperature=0):
    """Return the model's text answer to `question`.

    `client` exists so tests can pass in a fake; normally a real Groq
    client is created, which picks up GROQ_API_KEY automatically.

    `temperature` controls randomness.  The default of 0 makes the
    model pick its most likely answer, so the same question gives a
    more consistent reply from one run to the next.

    If `model` is rate limited, the question is sent to
    `FALLBACK_MODEL` instead.  If that is rate limited too, Groq's
    error is raised.
    """
    if not question or not question.strip():
        raise ValueError("question must not be empty")

    client = client or Groq()

    def complete(name):
        response = client.chat.completions.create(
            model=name,
            temperature=temperature,
            messages=[{"role": "user", "content": question}],
        )
        return response.choices[0].message.content

    fallback = FALLBACK_MODEL if FALLBACK_MODEL != model else ""
    if fallback and time.monotonic() < _skip_until.get(model, 0):
        return complete(fallback)
    try:
        return complete(model)
    except groq.RateLimitError as error:
        if not fallback:
            raise
        _skip_until[model] = time.monotonic() + SKIP_SECONDS
        logger.warning("%s is rate limited (%s); using %s instead",
                       model, error, fallback)
        return complete(fallback)


if __name__ == "__main__":
    print(ask("In one sentence, what is retrieval-augmented generation?"))
