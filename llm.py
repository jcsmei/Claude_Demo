"""Send a question to a Groq-hosted language model and return its reply."""

import os

from dotenv import load_dotenv
from groq import Groq

# Read GROQ_API_KEY (and optionally GROQ_MODEL) from the .env file.
load_dotenv()

DEFAULT_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")


def ask(question, client=None, model=DEFAULT_MODEL, temperature=0):
    """Return the model's text answer to `question`.

    `client` exists so tests can pass in a fake; normally a real Groq
    client is created, which picks up GROQ_API_KEY automatically.

    `temperature` controls randomness.  The default of 0 makes the
    model pick its most likely answer, so the same question gives a
    more consistent reply from one run to the next.
    """
    if not question or not question.strip():
        raise ValueError("question must not be empty")

    client = client or Groq()
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[{"role": "user", "content": question}],
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    print(ask("In one sentence, what is retrieval-augmented generation?"))
