# Retrieval-augmented generation

Retrieval-augmented generation (RAG) gives a language model access to
documents it was never trained on. Before the model answers, the
system looks up passages related to the question and places them in
the prompt.

Documents are first split into chunks. Each chunk is converted into an
embedding, a list of numbers that represents its meaning. Chunks with
similar meanings have embeddings that are close together.

A vector database such as Chroma stores the embeddings. At question
time, the question is embedded the same way and the database returns
the nearest chunks.
