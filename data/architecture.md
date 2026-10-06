# Technical overview of this assistant

## Technical overview: tell me about this bot

A technical overview of this bot: it is an AI assistant that answers
from four sources and shows the evidence for each answer. Its parts
are a Streamlit chat page, a LangGraph decision flow, RAG over a
knowledge base stored in Chroma, live tools for GitHub, NYC Open Data
and web search, an MCP server and client, and language models hosted
by Groq.

## What are the four sources this bot answers from?

The bot answers from four sources. Its knowledge base, searched by
meaning with RAG. GitHub, called live for the project's recent code
changes. NYC Open Data, queried live with SQL for counts of taxi
driver licenses. And the web, searched through Tavily's MCP server,
only when the knowledge base does not cover a question. Every answer
names which source it came from.

## What is the technology stack of this assistant?

The stack has seven layers. Streamlit provides the chat page.
LangGraph orchestrates the decision flow. Chroma is the vector store,
with the all-MiniLM-L6-v2 embedding model. Groq hosts the language
models: openai/gpt-oss-20b for answers, openai/gpt-oss-120b as a
fallback, and Llama Prompt Guard for screening. The MCP Python SDK
provides the MCP server and client. GitHub, NYC Open Data and Tavily
supply live data. Everything is written in Python 3.12.

## How does one message flow through the system, step by step?

A message passes through six steps. One: screen it, and refuse it if
it is too long or looks like a prompt injection. Two: choose a tool,
which is the documents, GitHub or NYC data. Three: fetch, meaning
retrieve passages, get commits or run a SQL query. Four: fall back to
a web search only if the documents did not cover the question. Five:
the model writes the answer from what was fetched and nothing else.
Six: the page shows the source and the evidence.

## What is the knowledge base?

The knowledge base is the set of source documents the assistant is
allowed to answer from. In this project it is the Markdown files in
the folder named data, written as questions and answers. It is the
single source of truth: to change what the assistant knows, you edit
the knowledge base, not the model. Another common word for it is the
corpus.

## What is the difference between the knowledge base, the vector store and the index?

The knowledge base is the source documents, which people write and
maintain. The vector store is the database that holds the embeddings;
here it is Chroma. The index is the searchable copy built from the
knowledge base and kept in the vector store. The knowledge base is
the source of truth, and the index is derived from it and can be
rebuilt at any time. If the two fall out of step, the assistant
answers from old content, which happened once in this project.

## What is the ingestion pipeline, also called the indexing pipeline?

The ingestion pipeline turns the knowledge base into a searchable
index in three steps. Chunk: split each document at its headings, so
each chunk holds one question and its answer. Embed: convert each
chunk into a list of 384 numbers that represents its meaning. Store:
save each chunk with its embedding and source file in the vector
store. The pipeline runs at startup and again whenever a document
changes.

## What are the main components, and which file is each one in?

There are eight code files, each with one job. app.py is the chat
page. chat.py is the LangGraph decision flow. rag.py holds the
prompts and the answering logic. store.py does chunking, storage and
retrieval. tools.py fetches live data from GitHub, NYC Open Data and
the web. llm.py makes the model calls and handles the fallback.
guard.py screens messages for prompt injection. mcp_server.py is the
MCP server.

## What engineering terms describe the parts of this system?

The standard terms are these. Knowledge base or corpus: the source
documents. Ingestion or indexing: preparing them for search. Chunk: a
piece of a document. Embedding: numbers representing meaning. Vector
store: the database of embeddings. Retrieval and top-k: fetching the
k closest chunks. Grounding: making the model answer from sources.
Orchestration: controlling the order of steps. Tool routing: choosing
a tool for a question. Guardrail: a rule enforced by code. Fallback:
what runs when the first choice fails.

## What are the guardrails, in brief?

Guardrails are rules enforced by code, not left to the model. Each
message is screened for prompt injection and limited in length.
Instructions and outside text travel in separate roles. SQL is
restricted to one read-only SELECT. The tools are fixed in code.
Secrets never enter a prompt. Web searches are blocked for messages
about people or about the project itself. Web answers carry a warning
that they are not from the official documents.

## How many model calls does one answer take?

Every message gets one small screening call to a classifier. After
that, an answer from the documents or from GitHub takes two model
calls: one to choose the tool and one to write the answer. An answer
from the NYC data takes three: choose the tool, write the SQL, explain
the result. A web answer also takes three, because the documents are
tried first.

## What are the known limitations of the system?

The main limitations are these. Retrieval must find the answer in the
five passages it fetches. Questions about the whole collection, such
as a summary of everything, cannot be answered. The model trusts its
sources, so a wrong document gives a wrong answer. Instructions steer
the model but do not lock it. Prompt injection defences are not
complete. The free allowances are small. There are no user accounts.

## Where is the full technical specification?

The full technical specification is the file ARCHITECTURE.md in the
project's GitHub repository, at
https://github.com/jcsmei/Claude_Demo/blob/main/ARCHITECTURE.md
It covers every component in detail, with diagrams, the reason behind
each design choice, and a table of every parameter in the code. This
document is the short version of it.
