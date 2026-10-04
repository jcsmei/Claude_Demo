# About this project and this chat bot

## What is this project?

This project is a small learning demo of three ideas: RAG (retrieval-
augmented generation), MCP (Model Context Protocol) and LangGraph. It
answers questions from a small folder of documents and from two live
sources, GitHub and NYC Open Data, shows the evidence each answer came
from, and offers the same abilities to AI assistants as tools. It was
started in October 2026.

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

You can ask about six subjects in its documents: how RAG works, what
MCP is and which tools the project's MCP server offers, how LangGraph
directs the bot's decisions, the project itself and why each decision
was made, the problems that were found and fixed, and Jack Mei, its
creator. You can also ask two things it answers from live sources:
what changed in the code recently, from GitHub, and how many New York
City medallion taxi drivers hold an active license and when those
licenses expire, from NYC Open Data. A general question outside all of
these is answered from a web search, and the bot says so.

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
Groq over the internet and receives the answer back. A second model,
openai/gpt-oss-120b, is used as a backup when the first is rate
limited.

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
page. After that came conversation memory, the GitHub tool with tool
choice, the rebuild of the decision flow on LangGraph, and the SQL
tool for NYC Open Data. Building this way means that when something
breaks, the fault is in the one piece just added.

## How is the project tested?

The project has more than 180 automated tests, run with pytest. The
tests replace the language model, the embedding model, GitHub and NYC
Open Data with simple fakes, so they need no internet, cost nothing
and give the same result every time. A separate set of tests checks
retrieval with real questions and the real embedding model. Live runs
against the real services were done as well, and they caught bugs the
fakes could not.

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
for the language model, the MCP Python SDK 2.3.0 for the server, LangGraph 1.2.12 for the
decision flow,
Streamlit 1.65.0 for the chat page, and pytest for the tests.

## Is there a rate limit on questions?

Yes, three limits apply. Each visit is limited to 20 questions. The
project's Groq account, on the free tier, allows each model 8,000
tokens per minute and 200,000 tokens per day. A chat message uses
roughly 2,500 to 4,000 tokens across two or three model calls, so the
main model can answer about 50 to 80 messages per day across all
visitors. When the main model reaches a limit, the bot switches to a
second model. Only if both are limited does the page say which limit
was reached and when to try again.

## How does the bot choose which tool to use?

For every message, the language model first chooses one of three
tools: the project's documents, GitHub for questions about recent code
changes, or NYC Open Data for counts of taxi driver licenses. The same
call rewrites a follow-up into a standalone question. The chosen tool
then fetches its information and the model answers from it. If the
documents do not cover a question, a fourth tool, a web search, is
tried. Each answer names its source underneath, so the reader always
knows where it came from.

## Can the bot tell me what changed in the code recently?

Yes. Questions such as "What changed in the code most recently?" are
answered from the project's live commit history on GitHub, not from
the documents. The answer lists the commits it was drawn from, each
with a link.

## Where does the taxi driver data come from?

The taxi driver numbers come from NYC Open Data, the City of New
York's public data site, from the dataset "Medallion Drivers - Active"
published by the Taxi and Limousine Commission. The city refreshes it
daily. The bot fetches it live through the city's API and keeps a copy
for six hours, so the numbers are current and are not stored in the
project.

## Why does the taxi driver data hold only counts and no names?

The source dataset lists about 180,000 individual drivers with their
names and license numbers. It is a public record, but a demo should
not become a tool for looking up named people. So the bot asks the
city's API for counts only, grouped by the month a license expires.
Names and license numbers are never downloaded, stored or shown.

## Why is the taxi data queried with SQL instead of searched like the documents?

Retrieval finds the few passages closest in meaning to a question.
That suits text, but it cannot total a column, count rows or filter by
year. A table is structured data, so the right approach is to query
it. The model writes a SQL statement, it runs on the table, and the
model answers from the rows returned. Using retrieval for text and SQL
for tables shows that different kinds of data need different tools.

## How is the SQL the model writes kept safe?

The SQL runs on a small temporary table that holds only public counts.
Only a single SELECT statement that reads that table is accepted, the
database is set to refuse any change, at most 50 rows are returned,
and a query that runs too long is stopped. If the SQL fails or returns
nothing, the error is shown to the model for one corrected attempt.
The page shows the SQL and the rows under each answer.

## Can the bot reach data in more than one place?

Yes. In a company, information lives in many systems, and this demo
shows the same idea on a small scale. The bot draws on four sources:
its own documents, searched by meaning; GitHub, called live for recent
code changes; NYC Open Data, queried live with SQL; and the web,
searched through a service named Tavily when the documents do not
cover a question.

## What happens when the tokens run out and the model's allowance is used up?

Groq counts its limits separately for each model. When the main model,
openai/gpt-oss-20b, is rate limited, the bot sends the same question
to a second model on the same account, openai/gpt-oss-120b, so
visitors still get an answer. The main model is then skipped for ten
minutes, so that later questions do not each wait on a request that
would be refused. Every switch is written to the log. If both models
are rate limited, the page says so. This was chosen over a mode that
only shows search results, because the bot should stay able to answer.

## When does the bot search the web?

Only when its own documents do not cover a general question. The bot
always tries the documents first, and they are never overridden by the
web. A question about this project itself is never searched on the
web, because the web knows nothing about this project; if the
documents do not cover it, the bot says so. A web answer is marked
three ways: a highlighted warning that it comes from web pages and not
from the project's official documents, a source line naming the web
search, and a list of the pages used, with links. Web pages are not
verified by this project.

## Why are questions about the creator never searched on the web?

A question that names Jack Mei, the project's creator, is never sent
to a web search. What the documents say about him is all the bot will
say, so a question such as his phone number is refused instead of
looked up online. This is a deliberate privacy rule in the code, not a
choice left to the model.

## How does the bot protect personal information and PII?

Five safeguards protect personal information. The taxi data holds
counts only: driver names and license numbers are never downloaded.
The GitHub tool leaves out author names and email addresses. A
question that names the project's creator is never sent to a web
search. Nor is a message that contains an email address or a phone
number, so the bot cannot be used to look a person up. And the
creator's own phone number and email are not in the documents;
LinkedIn is the only contact route. These are rules in the code,
checked by automated tests.

## What is sent to outside services when I ask a question?

Your question and the passages retrieved for it are sent to Groq,
which runs the language model. If the documents do not cover the
question and a web search is allowed, the question is also sent to
Tavily, the search service. Questions about code changes call GitHub,
and questions about taxi drivers call NYC Open Data, but neither is
sent your question. The conversation is kept only for the current
visit and is not stored afterwards, apart from the hosting service's
own logs.

## How does the bot stay usable when something fails?

The bot is built to keep answering. If the main language model is rate
limited, a second model takes over. If a SQL query fails or returns
nothing, it is corrected once. If the web search is unavailable, the
visitor gets the normal refusal with a note instead of an error. If a
tool fails outright, the page explains which stage failed and stays
usable for the next question.
