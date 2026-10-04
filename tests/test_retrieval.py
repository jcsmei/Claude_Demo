"""Check that real questions retrieve the passage holding their answer.

Unlike the other tests, this one uses the real embedding model and the
real documents in data/, because retrieval quality depends on both.
It needs no API key, but the first run downloads the embedding model
(about 80 MB).  Run it after every change to the documents: a new
passage can push an older one out of the results.
"""

import uuid

import chromadb
import pytest

from rag import DATA_FOLDER
from store import add_documents, get_collection, search

# The number of passages rag.answer retrieves by default.
TOP_K = 5

# Each question, and text that only the passage answering it contains.
CASES = [
    # How RAG works
    ("What is RAG?", "stands for retrieval-augmented generation"),
    ("what are chunks?", "cutting a textbook into index cards"),
    ("What is a chunk, and why are documents split into chunks?",
     "three reasons for chunking"),
    ("what does distance mean?", "how far apart"),
    ("How do I read the distance numbers?", "Lower distance is a closer"),
    ("What is an embedding?", "list of numbers that represents"),
    ("What embedding model is used?", "all-MiniLM-L6-v2"),
    ("How many chunks are retrieved?", "keeps the five closest"),
    ("why does the bot refuse some questions?", "fixed marker"),
    ("Why would a company like Pfizer want this?", "Traceability"),
    ("What can't you answer?", "There are four limits"),
    ("Has retrieval ever failed?", "ranked fifth"),
    # MCP
    ("What is MCP?", "stands for Model Context Protocol"),
    ("What tools does the MCP server have?",
     "four tools: search_documents, ask_documents,"),
    ("What does search_documents return?", "a number k from 1 to 10"),
    ("Why are search and ask separate MCP tools?",
     "serve different callers"),
    ("Does the chat page use MCP?", "calls the RAG code directly"),
    ("What does the MCP server log?", "logs/mcp_server.log"),
    # The project
    ("What is the project codename?", "codename is Blue Heron"),
    ("When is the design review?", "12 November 2026"),
    ("Which language model writes the answers, and why that one?",
     "openai/gpt-oss-20b, an open-weight"),
    ("Why Groq?", "offers a free tier"),
    ("Why python 3.12?", "began on Python 3.14"),
    ("How do you keep the API key safe?", "never written in the code"),
    ("How was this project built?", "an AI coding assistant"),
    ("Did an AI write this code?", "an AI coding assistant"),
    ("Where can I see the code?", "github.com/jcsmei/Claude_Demo"),
    ("What is this chat bot, and how does it know about itself?",
     "self-awareness is retrieval"),
    # Problems found and fixed
    ("What problems did the project run into?", "seventeen problems"),
    ("What bugs did you find?", "seventeen problems"),
    ("What is the STAR format?", "Situation, Task, Action, Result"),
    ("What was the biggest lesson learned?", "running the real system"),
    ("Why did the live app show old answers?", "fingerprint"),
    ("What went wrong with the disk?", "No space left on device"),
    ("Why not use a distance cutoff?", "cutoff"),
    ("Did the bot ever give a wrong answer?", "approximately seven"),
    ("How do you catch regressions in retrieval?", "over 40 real"),
    ("What happened with the MCP library version?", "MCPServer"),
    ("Why did the answers feel rigid?", "no conversation memory"),
    # Conversation
    ("Does the bot remember the conversation?", "last two exchanges"),
    ("What is query rewriting?", "This is called query rewriting"),
    ("What happens if I just say hi?", "second fixed marker"),
    ("Why is the temperature 0?", "most likely answer each time"),
    ("Is there a rate limit?", "8,000 tokens per minute"),
    ("What does the recent_commits tool do?", "newest first"),
    ("How does the bot choose which tool to use?",
     "first chooses one of three"),
    ("Can the bot tell me what changed recently?",
     "live commit history"),
    ("What does the query_license_data tool do?",
     "one read-only SQL query"),
    ("Does the project use LangGraph?", "is a LangGraph graph"),
    ("where does the taxi data come from?", "NYC Open Data"),
    ("Why are there no driver names in the data?", "counts only"),
    ("Why use SQL instead of RAG for the taxi data?",
     "cannot total a column"),
    ("How is the SQL kept safe?", "single SELECT statement"),
    ("Can the bot reach data in more than one place?",
     "draws on four sources"),
    ("Did testing ever break the live app?", "daily allowance"),
    ("Is there a daily limit?", "200,000 tokens per day"),
    ("What happens when the tokens run out?",
     "sends the same question to a second model"),
    ("When does the bot search the web?",
     "Only when its own documents do not cover"),
    ("Will the bot look up Jack on the web?",
     "never sent to a web search"),
    ("How does the bot protect personal information?",
     "Five safeguards protect personal information"),
    ("How do you handle PII?",
     "Five safeguards protect personal information"),
    ("What is sent to outside services?", "also sent to Tavily"),
    ("Are web answers from the official documents?",
     "not from the project's official documents"),
    ("What happens when something fails?", "built to keep answering"),
    ("can rag-demo call tools on another bot's MCP server?",
     "does not contain an MCP client"),
    ("Can another bot use this project's tools?",
     "if that bot is an MCP client"),
    ("Is the MCP server a web service?", "a local program"),
    ("Has a web answer ever been wrong?",
     "presented them as facts about this one"),
    ("What is LangGraph?", "flowchart on a whiteboard"),
    ("How does this bot use LangGraph?", "for its decision flow"),
    ("What are nodes and edges?", "A node is one step"),
    ("What steps are in the graph?", "graph has seven nodes"),
    ("What is the retry loop?", "handles a failed database query"),
    ("What is state in LangGraph?", "shared notebook"),
    ("How do RAG, MCP and LangGraph fit together in this project?",
     "Each answers a different question"),
    ("How would you add a new tool?", "three small changes"),
    # The creator
    ("Who built this demo, and what is his background?",
     "technical solutions architect based in New York"),
    ("How can I contact Jack?", "linkedin.com/in/jcsmei209"),
    ("Where has Jack worked?", "worked for six employers"),
    ("What companies has Jack worked for?", "worked for six employers"),
    ("What is Jack's work history?", "9 years of experience with six"),
    ("How many years of experience does Jack have?",
     "9 years of professional experience"),
    ("What does Jack do at IBM?", "IBM Cloud Object Storage"),
    ("What did he do at Sigma?", "4,000 tickets"),
    ("What experience does Jack have with AI agents?", "LangGraph"),
    ("Does Jack know Snowflake?", "Snowflake, Databricks and Google"),
    ("Does Jack need visa sponsorship?", "US citizen"),
    ("Is Jack open to remote work?", "Central or Eastern time zones"),
    ("Where did Jack go to school?", "CUNY School of Professional"),
]


@pytest.fixture(scope="module")
def collection():
    """Index the real documents once, in memory, for all the cases."""
    collection = get_collection(
        client=chromadb.EphemeralClient(),
        name=f"retrieval-{uuid.uuid4().hex}",
    )
    add_documents(collection, DATA_FOLDER)
    return collection


@pytest.mark.parametrize("question, expected", CASES)
def test_question_retrieves_its_answer(collection, question, expected):
    # Documents are wrapped at 70 characters, so compare with the line
    # breaks turned into spaces.
    passages = [" ".join(result["text"].split())
                for result in search(collection, question, k=TOP_K)]
    assert any(expected in passage for passage in passages), (
        f"No top-{TOP_K} passage for {question!r} contains {expected!r}"
    )
