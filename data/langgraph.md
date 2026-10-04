# LangGraph and how this bot decides what to do

## What is LangGraph?

LangGraph is a tool for laying out the steps an AI assistant follows,
and the rules for moving from one step to the next. Think of a
flowchart on a whiteboard: boxes for the steps and arrows between
them. LangGraph turns that flowchart into working software. It is
widely used to build AI assistants that have to make decisions, not
just answer in one step.

## How does this bot use LangGraph?

This bot uses LangGraph for its decision flow. Every message goes
through the same flowchart: first choose a source, then fetch the
information, then answer. LangGraph runs that flowchart. It is what
lets the bot answer one question from its documents, the next from
GitHub and the next from live city data, and fall back to a web search
when its documents do not cover something.

## Does the project use LangGraph, and why?

Yes. The decision flow in the file chat.py is a LangGraph graph. The
project started in plain Python, because the flow was a straight line:
search, then answer. LangGraph was adopted when the flow gained
branches and a retry loop, which is what a graph library is for. The
order matters: a framework was added when the problem needed one, not
before.

## What are nodes and edges in LangGraph?

A node is one step, a box in the flowchart: a small piece of code
that does one job, such as searching the documents. An edge is an
arrow from one node to the next. A conditional edge is an arrow with a
decision on it: the flow goes one way or another depending on what
just happened. The whole flowchart is called a graph.

## What are the steps in this bot's graph?

This bot's graph has seven nodes. choose_tool decides which source
fits the message. documents answers from the project's documents.
web_search answers from the web when the documents do not cover the
question. github answers from the project's recent code changes.
write_sql writes a database query for the taxi data, run_sql runs it,
and data_answer explains the result.

## Where does the graph make decisions?

The graph makes three decisions, each a conditional edge. After
choose_tool, it goes to the documents, to GitHub or to the taxi data.
After documents, it goes to a web search only if the documents did not
cover the question and a web search is allowed. After run_sql, it goes
back to write_sql once if the query failed or returned nothing.

## What is the retry loop in the graph?

The retry loop handles a failed database query. The language model
writes the query, and models sometimes make mistakes. If the query
fails or returns nothing, the graph sends the error back to the model
and asks for a corrected query, once. If the second attempt also
fails, the bot reports the failure. A loop like this is awkward in
plain code and natural in a graph.

## What is state in LangGraph?

State is the shared notebook that every node reads from and writes
to. In this bot the state holds the visitor's question, the recent
conversation, the tool that was chosen, the question rewritten for
searching, any database query and its error, and the final answer.
Each node adds its part, and the next node picks up from there.

## Does LangGraph do the thinking?

No. LangGraph only directs the flow: it decides which step runs next.
The thinking is done inside the steps, where the language model on
Groq is called. This project uses LangGraph for orchestration only and
keeps its own tested code for calling the model, searching the
documents and fetching outside data.

## How is the diagram on the page made?

The diagram in the sidebar, under "How the bot decides", is generated
from the LangGraph graph itself each time the page loads. It is not a
drawing kept beside the code, so it cannot fall out of date. Dashed
arrows are the decisions; solid arrows are steps that always follow.

## How would a new tool be added to the graph?

Adding a tool takes three small changes: a new node that does the
tool's work, one line describing when the tool should be chosen, and
an edge connecting it. The rest of the graph is untouched. That is
the practical benefit of a graph: each source of information is a
separate, replaceable part.

## How do RAG, MCP and LangGraph fit together in this project?

Each answers a different question. RAG is how the bot finds answers
in its own documents: it looks the answer up before replying.
LangGraph is how the bot decides where to look: documents, GitHub,
city data or the web. MCP is how other AI assistants can use the same
abilities: it is a standard plug for tools. One shared core, reached
through a chat page for people and through MCP for assistants.

## Which version of LangGraph does the project use?

The project uses LangGraph 1.2.12. It uses the graph features only:
StateGraph, nodes, edges and conditional edges. It does not use
LangChain's model wrappers.
