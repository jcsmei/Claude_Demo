# MCP and this project's MCP server

## What is MCP?

MCP stands for Model Context Protocol. It is an open standard for
connecting AI assistants to outside tools and data. Think of it as a
universal plug: a tool built once as an MCP server works with any
assistant that speaks MCP, with no custom integration code for each
one.

## What are an MCP server and an MCP client?

An MCP server is a program that offers capabilities. An MCP client is
the AI assistant that calls them. A server can offer tools, which are
functions the assistant may call, and resources, which are data the
assistant may read. Each tool has a name, a description and a typed
list of inputs, so the assistant knows when and how to use it.

## What tools does the MCP server have?

The MCP server has three tools: search_documents, ask_documents and
recent_commits.

## Where are the MCP tools defined?

All three tools, search_documents, ask_documents and recent_commits,
are defined in the file mcp_server.py. The server is named rag-demo.

## What does the search_documents tool do?

The search_documents tool takes a query and a number k from 1 to 10,
with a default of 3. It returns the k passages closest in meaning to
the query. Each passage comes with its text, the source file it came
from and its distance from the query. This tool only does retrieval:
it does not call the language model, so it costs no model tokens.

## What does the ask_documents tool do?

The ask_documents tool takes a question and runs the full RAG
pipeline: it retrieves the five closest chunks and asks the language
model on Groq to answer from them. It returns the answer and the list
of source files. When the documents do not contain the answer, the
answer says so and the list of sources is empty.

## What does the recent_commits tool do?

The recent_commits tool returns the project's most recent commits from
GitHub, newest first. Each commit comes with its short ID, its date,
the first line of its message and a link. It calls GitHub's public API
live, so it shows changes made after these documents were written.
Author names and email addresses are left out. Results are reused for
ten minutes, because GitHub limits how often its API may be called
without a login.

## Why does the MCP server have separate tools for searching and for asking?

The two tools serve different callers. An AI assistant such as Claude
can write its own answer, so it often needs only the passages:
search_documents gives it those quickly and without spending Groq
tokens. ask_documents is for a caller that wants a finished answer.
Keeping the tools separate lets the assistant choose the cheaper one.

## How is the MCP server built and run?

The server is written with the official MCP Python SDK, version 2.3.0,
using its MCPServer class. It is started with the command "python
mcp_server.py". It talks to its client over standard input and output,
which is why nothing in the project may print to standard output while
the server runs: that would corrupt the protocol.

## How does an AI assistant connect to the MCP server?

The file .mcp.json in the project tells Claude Code how to start the
server. When the project is opened in Claude Code and the server is
approved, the tools become available to the assistant. This was
tested: the assistant called both tools and found the project
codename.

## Does the chat page use the MCP server?

No. The Streamlit chat page calls the RAG code directly, because the
page is the project's own Python code and can import the function. MCP
exists so that outside AI assistants can use the same abilities. The
design is one shared core with two front ends: the MCP server for
assistants and the chat page for people. The chat page chooses
between the same tools by itself.

## How does the MCP server handle errors?

Bad input, such as an empty query or a k outside 1 to 10, is rejected
with a clear message that is passed back to the assistant so it can
correct itself. An unexpected crash is reported to the assistant only
as a generic failure, because raw error text could expose something
sensitive. The full detail goes to the log file instead.

## What does the MCP server log?

Every tool call is written to the file logs/mcp_server.log: the tool
name and its inputs, how long the call took, any rejected input with
the reason, and any unexpected failure with its full traceback. The
logging exists so that no tool call fails silently and so that
problems can be traced afterwards, which also shows due diligence in a
company setting.
