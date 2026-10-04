# How this demo answers questions (RAG)

## What is RAG?

RAG stands for retrieval-augmented generation. It is a way to make a
language model answer from a chosen set of documents instead of from
its own memory. Before the model answers, the system retrieves the
passages most related to the question and places them in the prompt.
The model then writes its answer from those passages.

## What are the three steps of RAG?

Retrieve, augment, generate. Retrieve: search the stored documents for
the passages closest in meaning to the question. Augment: add those
passages to the prompt next to the question. Generate: the language
model writes an answer using only those passages.

## What is a chunk?

A chunk is a small piece of a document, usually a paragraph or two.
Before anything is stored, each document is cut into chunks. Think of
cutting a textbook into index cards: each card holds one idea and can
be pulled out on its own. In this demo a chunk is made of whole
paragraphs and holds up to about 500 characters.

## Why are documents split into chunks instead of used whole?

There are three reasons for chunking. Precision: the search can return
the one paragraph that answers the question instead of a whole file.
Cost and speed: models charge by the amount of text they read, so a
few short chunks are cheaper and faster than every document. Limits: a
model can only read so much text at once, and a large company has far
more documents than would fit.

## How does this demo make its chunks?

The chunking splits each document at blank lines, so a paragraph is
never cut in the middle of a sentence. A new chunk starts at every
heading, so each chunk covers one topic and carries its heading with
it. Paragraphs under the same heading are packed together until adding
another would pass about 500 characters. The function that does this
is chunk_text in the file store.py.

## What is an embedding?

An embedding is a list of numbers that represents the meaning of a
piece of text. An embedding model reads a chunk and produces the list.
Texts with similar meanings get similar numbers even when they use
different words: "How do I reset my password" and "I forgot my login"
land close together. In this demo each embedding is a list of 384
numbers.

## Which embedding model does this demo use?

The embedding model is all-MiniLM-L6-v2, the default of the Chroma
database. It is small and runs on the same computer as the app, so
making embeddings needs no outside service and costs nothing. It was
chosen because it is the default and is good enough for a small demo.
It is a different model from the language model that writes the
answers.

## What is a vector database, and what is Chroma?

A vector database stores embeddings and can quickly find the stored
ones closest to a new one. Chroma is the open-source vector database
used in this demo. It stores every chunk together with its embedding
and the name of the file the chunk came from.

## What is distance?

Distance is a number that says how far apart two pieces of text are in
meaning. The question is turned into an embedding the same way the
chunks were, and the database measures how far the question's
embedding is from each chunk's embedding. A small distance means the
chunk is about the same thing as the question. A large distance means
the chunk is about something else.

## How do I read the distance numbers shown under an answer?

Lower distance is a closer match. A distance of 0 would mean the chunk
and the question mean exactly the same thing, and values near 2 mean
the chunk is unrelated to the question. In the project's own tests the
strongest matches scored below 1 and off-topic questions scored about
1.85 or higher. The app shows the distance beside each retrieved
passage so that anyone can judge how good the search was.

## How is distance calculated?

Technically, the distance in this demo is the squared Euclidean
distance, also called squared L2, between the embedding of the
question and the embedding of the chunk. It is the default distance
measure in Chroma.

## How many chunks are retrieved for each question?

Five. The search ranks every stored chunk by distance and keeps the
five closest. Only those five chunks are shown to the language model,
and the app lists them under each answer as the retrieved passages.

## Has retrieval ever failed in this project?

Yes. The project first retrieved three chunks per question. In
testing, the question "What tools does the MCP server have?" was
refused even though the answer was in the documents: the chunk holding
it ranked fifth, behind general chunks about MCP. The fix had three
parts: retrieve five chunks, start a new chunk at every heading so
that each chunk holds one question and its answer, and make that
answer shorter and more focused. It shows that in RAG the search
matters as much as the model.

## Why does the bot only answer from the documents?

Two things keep the bot on the documents. First, retrieval controls
what the model sees: only the five closest chunks are placed in the
prompt. Second, the prompt instructs the model to answer using only
those chunks. The model still has everything it learned in training,
so the instruction is a strong steer and not an absolute lock.

## Why would a company want a bot limited to its own documents?

There are four reasons. Accuracy: an invented answer about a policy or
a medicine dose is far worse than no answer. Traceability: every
answer points to its source passages, so a person can check it.
Private and current knowledge: the model was never trained on internal
documents, and updating a document updates the answers with no
retraining. Access control: the company decides which documents the
bot can search.

## Why does the bot refuse some questions it cannot answer?

The prompt tells the model to reply with a fixed marker when the
retrieved chunks do not contain the answer. The code detects the
marker and shows a standard message saying the documents do not
contain an answer. The app still lists the closest passages it found,
labelled as not containing the answer, so the viewer can see that the
search ran.

## Why does the bot not use a distance cutoff to refuse questions?

A distance cutoff was measured and rejected. In a test of nine
questions, one unanswerable question had a closer best match (1.05)
than one answerable question (1.65). Any cutoff would have blocked a
good question or let a bad one through. So the decision to refuse is
left to the model reading the chunks.

## What are the limits of RAG, and what can this bot not answer?

There are four limits. Retrieval has to find the answer: it must be in
the five closest chunks. Questions about the whole collection fail,
such as "summarise every document". An answer split across chunks can
be missed if only part is retrieved. And the model trusts the
documents, so a wrong document gives a confidently wrong answer.

## Does the bot remember the conversation and handle follow-up questions?

Yes. The last two exchanges of the conversation are included in the
prompt, so the model knows what a follow-up refers to. If you say you
did not understand, it explains the same facts again more simply. The
memory lasts only for the current visit; nothing is stored afterwards.

## How does the bot search for a follow-up question? What is query rewriting?

A follow-up such as "What tools does it have?" means nothing to the
search on its own. So before searching, the language model rewrites
the follow-up into a standalone question, for example "What tools does
the MCP server have?". This is called query rewriting. It costs one
small extra model call, and only on follow-ups. The page shows the
rewritten question with the retrieved passages.

## What happens when a message is a greeting, thanks or unclear?

The model is told to reply with a second fixed marker when a message
is only a greeting or thanks, or is too unclear to answer. The code
detects that marker and replies with a short list of what the bot can
help with. This is different from a real question the documents do
not cover, such as the capital of France, which is still refused.

## Why is the model's temperature set to 0?

Temperature controls how much randomness the model uses when choosing
words. At 0 it picks its most likely answer each time. It was set to 0
after the same question, with the same retrieved passages, listed
every item on one run and only two on another. A temperature of 0
makes answers more consistent from run to run; it does not make them
perfectly identical.

## How is new information added to the bot?

Add a file ending in .md or .txt to the data folder, or edit an
existing one. When the app restarts, every document is chunked and
stored again, and chunks from removed text are deleted. No retraining
of any model is needed, which is one of the main advantages of RAG.
