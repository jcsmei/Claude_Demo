"""Screen a message for prompt injection before the model sees it."""

import logging
import os

from llm import ask

# A small classifier hosted by Groq.  It replies with a number from 0
# to 1: how likely the text is an attempt to override instructions.
# Set to an empty value to turn screening off.
GUARD_MODEL = os.getenv("GROQ_GUARD_MODEL",
                        "meta-llama/llama-prompt-guard-2-86m")
THRESHOLD = 0.5
# The classifier reads only a short text, so longer ones are cut.
MAX_GUARD_CHARS = 1500

logger = logging.getLogger("rag_demo.guard")


def injection_score(text, client=None):
    """Return the classifier's score for `text`, or None if unknown.

    None means the classifier is switched off, could not be reached or
    gave an unreadable reply.  The failure is logged.
    """
    if not GUARD_MODEL:
        return None
    try:
        reply = ask(text[:MAX_GUARD_CHARS], client=client,
                    model=GUARD_MODEL, fallback=False)
        return float(reply.strip())
    except Exception as error:
        logger.warning("injection screening unavailable: %s",
                       type(error).__name__)
        return None


def looks_like_injection(text, client=None):
    """Return True if `text` is probably a prompt injection attempt.

    When the score is unknown the answer is False.  Screening is one
    layer of several, so a failure here lets the message through to
    the others instead of taking the whole bot down.
    """
    score = injection_score(text, client=client)
    if score is not None and score >= THRESHOLD:
        logger.warning("message flagged as prompt injection (%.2f)", score)
        return True
    return False
