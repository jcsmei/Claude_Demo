"""Stand-ins for external services, so tests need no network or tokens."""

import zlib
from types import SimpleNamespace

from chromadb import EmbeddingFunction

EMBEDDING_SIZE = 64


class FakeClient:
    """Mimic the part of the Groq client that ask() uses.

    The keyword arguments of the last call are kept in `received`.
    """

    def __init__(self, reply):
        self.reply = reply
        self.received = None
        completions = SimpleNamespace(create=self._create)
        self.chat = SimpleNamespace(completions=completions)

    def _create(self, **kwargs):
        self.received = kwargs
        message = SimpleNamespace(content=self.reply)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeEmbedding(EmbeddingFunction):
    """Embed text by counting its words, without downloading a model.

    Texts that share words get similar vectors, which is enough to
    test storage and retrieval.
    """

    def __init__(self):
        pass

    @staticmethod
    def name():
        return "fake"

    def get_config(self):
        return {}

    @staticmethod
    def build_from_config(config):
        return FakeEmbedding()

    def __call__(self, input):
        vectors = []
        for text in input:
            vector = [0.0] * EMBEDDING_SIZE
            for word in text.lower().split():
                word = word.strip(".,?!:;()[]#")
                if word:
                    index = zlib.crc32(word.encode()) % EMBEDDING_SIZE
                    vector[index] += 1.0
            vectors.append(vector)
        return vectors
