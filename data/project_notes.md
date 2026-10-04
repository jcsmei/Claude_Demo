# About this project and this chat bot

## What is this project?

This project is a small learning demo of two ideas: RAG
(retrieval-augmented generation) and MCP (Model Context Protocol). It
answers questions from a small folder of documents, shows the passages
each answer came from, and offers the same ability to AI assistants as
tools. It was started in October 2026.

## Who created this demo?

The creator and developer of this demo is Jack Mei. His LinkedIn
profile is https://www.linkedin.com/in/jcsmei209/

## How was this project built?

Jack Mei, a solution architect and engineer, built this project using
Claude Code, an AI coding assistant. Jack acted as the architect: he
set the goals, chose the technologies, made the design decisions and
reviewed each step. The assistant wrote the code and the tests and ran
them. The first working prototype took about three hours.

## Which decisions did the architect make?

Jack Mei made the key decisions: to test each component before
starting the next, to add logging so that no tool call fails silently,
to move to Python 3.12 for hosting, to put the chat page behind a
password, to show technical error details to viewers, and to make the
bot able to explain itself to any reader, technical or not.

## Where is the code for this project?

The code is public on GitHub at https://github.com/jcsmei/Claude_Demo/
The repository holds all the source code, the automated tests, the
documents this bot searches, and a README that explains how to set up
and run the project.

## What is this chat bot, and how does it know about itself?

This chat bot is the demo's front end. It has no built-in knowledge of
itself. It can describe how it works only because its own design was
written down in the documents it searches, and it searches them like
any others. Its self-awareness is retrieval: if a fact about the
project is not in the documents, the bot will say it does not know.

## What can I ask this bot?

You can ask about five subjects, one per document. How RAG works:
chunks, embeddings, distance and why the bot refuses some questions.
What MCP is and which tools this project's MCP server offers. The
project itself: which language model it uses, how it was built and why
each decision was made. Jack Mei, its creator: his experience, skills
and how to contact him. And the problems the project ran into, with
how each one was found and fixed.

## What are the parts of this project?

The project has seven main code files. llm.py sends a question to the
language model. store.py splits documents into chunks, stores them in
Chroma and searches them. rag.py joins the two: it retrieves chunks
and asks the model to answer from them. tools.py fetches live
information from outside, such as GitHub. chat.py chooses which tool
fits each message. mcp_server.py offers the tools to AI assistants.
app.py is the chat page.

## Which language model (LLM) does this bot use?

The answers are written by the model openai/gpt-oss-20b, an
open-weight language model published by OpenAI with about 20 billion
parameters. The model is run by Groq, a company that hosts language
models and serves them through an API. The app sends the prompt to
Groq over the internet and receives the answer back.

## Why was this language model chosen?

In RAG the answer is already in the retrieved passages, so the model's
job is to read a few paragraphs and answer from them. That does not
need a large model. A small model is faster and cheaper, and
openai/gpt-oss-20b followed the instruction to answer only from the
passages in the project's tests. It was picked from the models Groq
offered when the project was built.

## Why was Groq chosen to run the model?

Groq is known for very fast responses and offers a free tier, which
suits a demo. In the project's tests a full answer took under one
second.

## Can the language model be changed?

Yes. The model name is a setting called GROQ_MODEL, so another model
hosted by Groq can be used without changing any code. Because the
knowledge lives in the documents and not in the model, swapping the
model does not change what the bot knows.

## What is the project's codename, Blue Heron?

The project's codename is Blue Heron. The codename was
invented on purpose as a fact that no language model could know from
its training. When the bot answers "Blue Heron", it proves the answer
came from the documents and not from the model's memory.

## When is the design review?

The first design review for Blue Heron is scheduled for 12 November
2026, to cover retrieval quality and the MCP tool design. Like the
codename, this date is an invented fact placed in the documents to
prove that retrieval works.

## In what order was the project built?

One component at a time, each tested before the next was started:
first the call to the language model, then storage and search in
Chroma, then the two joined as RAG, then the MCP server, then the chat
page. Building this way means that when something breaks, the fault is
in the one piece just added.

## How is the project tested?

The project has more than 40 automated tests, run with pytest. The
tests replace the language model and the embedding model with simple
fakes, so they need no internet, cost nothing and give the same result
every time. Live runs against the real services were done separately,
and they caught bugs the fakes could not.

## How are the API key and password kept safe?

Secrets are never written in the code. On a developer's computer they
live in a file named .env, which is excluded from the code repository.
On the hosting service they are stored in its secrets settings. If an
error message ever contained a secret, the app replaces it with
"[redacted]" before showing it.

## Why is the chat page behind a password, with a question limit?

Each answer uses the project owner's Groq account. The password stops
strangers from using it, and if no password is configured the page
stays locked for everyone. Each visit is also limited to 20 questions.
The password is the real protection; the limit only guards against
accidents.

## How does the bot handle failures?

When something fails, the page says which stage failed, such as
generation at Groq, and whether asking again will help. A "Technical
details" section shows the real error type and message. The viewers
are expected to be technical enough to want that. The page keeps
working after a failure.

## Why does the project use Python 3.12?

The project began on Python 3.14, the newest version, and was moved to
3.12 before deployment because hosting services support older versions
more reliably. Moving was easy because the exact package versions are
recorded in a file named requirements.txt, so the environment can be
rebuilt with one command.

## Where is the chat page hosted?

The chat page is built with Streamlit, a Python library for making web
pages, and hosted on Streamlit Community Cloud, a free hosting
service. After a restart the first question is slow, because the
embedding model is downloaded and every document is chunked and stored
again.

## Which technologies does the project use?

Python 3.12, Chroma 1.5.9 as the vector database, the Groq SDK 1.7.0
for the language model, the MCP Python SDK 2.3.0 for the server,
Streamlit 1.65.0 for the chat page, and pytest for the tests.

## Is there a rate limit on questions?

Yes. Besides the limit of 20 questions per visit, the project's Groq
account allows 8,000 tokens per minute on its free tier. A question
uses roughly 1,100 to 1,500 tokens, mostly the retrieved passages, so
about six questions per minute can be answered across all visitors.
Beyond that the page says the rate limit was reached and asks the
visitor to wait a minute.

## How does the bot choose which tool to use?

For every message, the language model first chooses a tool: the
project's documents, or GitHub for questions about recent code
changes. The same call rewrites a follow-up into a standalone
question. The chosen tool then fetches its information and the model
answers from it. Each answer names its source underneath, so the
reader always knows whether it came from the documents or from GitHub.

## Can the bot tell me what changed in the code recently?

Yes. Questions such as "What changed in the code most recently?" are
answered from the project's live commit history on GitHub, not from
the documents. The answer lists the commits it was drawn from, each
with a link.
