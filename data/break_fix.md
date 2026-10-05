# Problems found and fixed while building this project

## What problems and bugs did the project run into?

The project ran into seventeen problems worth recording: a breaking
change in the MCP (Model Context Protocol) library, tool errors that hid their cause, a tool
that returned no structured data, a full disk, a chat box that ignored
the question limit, an unsupported Python version, a rejected idea for
refusing questions, a retrieval miss, a wrong fact about the creator,
a live app that searched old documents, questions that silently
stopped working, answers that felt rigid, follow-up questions that
searched for the wrong thing, a dataset that held personal data, SQL
that returned wrong or invented answers, testing that used up the
daily allowance of the language model, and a web answer that made
false claims about the project. Each one is described in its own section
in the STAR format.

## What is the STAR format used in the bug reports?

STAR stands for Situation, Task, Action, Result. Situation: what was
happening when the problem appeared. Task: what needed to be achieved.
Action: what was done to find the cause and fix it. Result: the
outcome, and the lesson. Every problem in this document is told in
that order.

## What is the main lesson from the problems in this project?

Most of the problems were found by running the real system, not by
the automated tests with fakes. Fakes prove the logic is right; only a
live run proves the parts work together. The other lesson is that in
RAG the search fails more often than the model: five of the seventeen
problems were retrieval problems, which is why the project now has
tests that check retrieval with real questions.

## Problem: the MCP library had a breaking change

Situation: the MCP server was about to be written, and the installed
MCP Python SDK was version 2, newer than the commonly documented
version 1. Task: write the server against the interface that was
actually installed. Action: before writing any code, the installed
package was inspected, which showed the main class had been renamed
from FastMCP to MCPServer. Result: the server worked on the first run.
Lesson: check the installed version of a library instead of assuming
its interface.

## Problem: MCP tool errors hid their cause

Situation: when an MCP tool received bad input, such as an empty
query, the AI assistant was told only "Error executing tool" with no
reason. Task: let the assistant see why its input was rejected so it
can correct itself. Action: a live probe showed the SDK treats an
ordinary error as a crash and hides its message; the tools were
changed to raise ToolError, the type whose message is passed on.
Result: the assistant now receives messages such as "k must be between
1 and 10", while real crashes still show only a generic message.

## Problem: an MCP tool returned no structured data

Situation: the ask_documents tool returned its answer as plain text
only, without the separate answer and sources fields. Task: return
structured data that an assistant can read reliably. Action: a live
run exposed it; the cause was a return type declared as a bare dict,
which gives the SDK nothing to build a schema from. The fields were
declared explicitly with a TypedDict. Result: the tool returns answer
and sources as data. Lesson: the unit tests passed, and only a live
end-to-end run revealed the fault.

## Problem: an install failed because the disk was full

Situation: installing Streamlit failed, and the reason was not visible
because the command's error output had been suppressed. Task: find the
real cause and complete the install. Action: the command was run again
with its output shown, which revealed "No space left on device": the
drive had 0.04 GB free. Pip's download cache was cleared and the
install repeated. Result: the install succeeded. Lesson: never hide
error output, because the error message is the fastest route to the
cause.

## Problem: the chat box ignored the question limit

Situation: each visit is limited to 20 questions, but after the last
allowed question the chat box stayed enabled. Task: make the page
reflect the limit immediately. Action: an automated test caught it;
the cause was that the chat box was drawn before the new question was
counted. The page now redraws straight after each answer. Result: the
chat box is disabled as soon as the limit is reached. The quota was
never at risk, because a further question would have been ignored.

## Problem: the Python version was too new for hosting

Situation: the project was built on Python 3.14, the newest version,
and the hosting service supported older versions more reliably. Task:
move the project to Python 3.12 without breaking it. Action: the
virtual environment was deleted and rebuilt on 3.12 from the pinned
versions in requirements.txt, then every test and a live run were
repeated. Result: everything passed on 3.12 within minutes. Lesson:
pinning versions makes an environment disposable and rebuildable.

## Problem: how should the bot refuse unanswerable questions?

Situation: for a question the documents could not answer, the bot
replied with a bare "I do not know" and still listed passages as if
they were useful. Task: refuse clearly and reliably. Action: a
distance cutoff was considered and then measured on nine questions;
an unanswerable question scored closer (1.05) than an answerable one
(1.65), so the cutoff was rejected. Instead the model returns a fixed
marker that the code detects. Result: a consistent refusal message,
and passages labelled as not containing the answer. Lesson: measure
before choosing a design.

## Problem: retrieval missed an answer that was in the documents

Situation: the question "What tools does the MCP server have?" was
refused, although the answer was in the documents. Task: make the
search find it. Action: inspecting the search results showed the right
chunk ranked fifth while only three were retrieved, because short
answers had been merged into unrelated neighbouring text. Three fixes
were made: retrieve five chunks, start a new chunk at every heading,
and write shorter, more focused answers. Result: the question is
answered correctly.

## Problem: the bot stated a wrong fact about its creator

Situation: asked how many years of experience Jack Mei has, the bot
answered "approximately seven"; the correct figure is 9. It also
listed only four of his six employers. Task: make answers about the
creator complete and correct. Action: the chunk stating the figure had
not been retrieved, so the model estimated from partial dates. Short,
direct answers were added for the questions people are most likely to
ask. Result: both questions are answered correctly. Lesson: the
instruction to use only the documents is a strong steer, not a lock.

## Problem: the live app answered from old documents

Situation: after new documents were published, the live app could not
answer questions about them and showed passages from the first
version. Task: make the live app search the current documents. Action:
the passages on screen were recognised as old text. The app caches its
index for speed, and the host updated the files without restarting the
process, so the index was never rebuilt. The cache was tied to a
fingerprint of the documents. Result: the index rebuilds whenever a
document changes.

## Problem: catching retrieval regressions, when working questions silently stop working

Situation: "What is the project codename?" had worked, then was
refused after more documents were added: new chunks had pushed the
right one out of the top five. It was noticed only by luck. Task:
detect this kind of regression automatically. Action: a retrieval test
was written with over 40 real questions, each paired with the text its
answer must retrieve, run against the real documents and embedding
model. Result: a document change that breaks any of those questions
now fails the tests before it reaches the live app.

## Problem: the answers felt rigid

Situation: in testing by the creator, the bot refused "I don't
understand", listed only two of eleven items, and recited passages
stiffly. The suspicion was that the language model was too small.
Task: find the real cause before changing the model. Action: the same
questions and passages were run through a larger model. It was no
better, and it invented a wrong meaning for MCP. The causes were in
the design: no conversation memory, a strict prompt, and random
variation. Result: the model was kept, and memory, a reply for unclear
messages, a temperature of 0 and a conversational prompt were added.

## Problem: follow-up questions searched for the wrong thing

Situation: with conversation memory added, "What tools does it have?"
was still refused after a discussion of MCP. Task: make the search
understand follow-ups. Action: the first design joined the earlier
messages to the new one for the search, with no extra model call.
Inspecting the results showed it found general MCP sections but not
the tools section. It was replaced by query rewriting: the model first
rewrites the follow-up as a standalone question. Result: follow-ups
are answered correctly, at the cost of one small extra model call.

## Problem: the chosen dataset held personal data

Situation: a public New York City dataset was chosen to show the bot
querying outside data. Task: add it as a tool. Action: before building
anything, the dataset was inspected. Its name suggested vehicles, but
it listed about 180,000 individual drivers with names and license
numbers. Result: the tool requests counts only from the city's API, so
no personal data is downloaded, stored or shown. Lesson: look at the
data before designing around it.

## Problem: the SQL tool gave wrong and invented answers

Situation: in a live check of the data tool, the model filtered on a
value that was not in the data, so a query matched nothing and the bot
reported "None"; another query returned invented text without reading
any data. Task: make data answers trustworthy. Action: the column that
invited the bad filter was removed, queries that read no data are
rejected, an empty result triggers one corrected attempt, and
questions about where the data comes from are sent to the documents.
Result: the same questions return the correct numbers.

## Problem: testing used up the daily allowance and took the live app offline

Situation: the bot's live checks and the public app share one Groq
account on the free tier. Only the limit of 8,000 tokens per minute
had been noticed. Task: verify the new tools against the real model.
Action: repeated live checks ran until Groq refused every call; its
message revealed a second limit of 200,000 tokens per day, nearly all
used. Result: the public app could not answer until the allowance
refilled. Three changes followed: live checks are rationed to a few
messages per change, the bot switches to a second model when the first
is rate limited, and the page explains the daily limit. Lesson: read a
service's limits before testing against a shared account.

## Problem: a web answer made false claims about the project

Situation: the creator asked whether the project could call tools on a
second bot. The documents did not cover it, so the bot searched the
web and answered that the project included an MCP client. At that time
it did not: the web pages described other projects, and the model
presented them as facts about this one. Task: stop web content being
passed off as project facts. Action: questions about the project
itself are no longer sent to web search, the model is told web pages
know nothing about this project, and the missing answers were added to
the documents. Result: the same question is answered correctly from
the documents.
