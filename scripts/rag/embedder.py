"""OpenAI embedding generation."""

from openai import OpenAI

from scripts.rag.config import EMBEDDING_BATCH_SIZE, EMBEDDING_MODEL


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts using OpenAI text-embedding-3-small.

    Handles batching for large inputs (max 2048 per API call).
    """
    client = OpenAI()
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[i : i + EMBEDDING_BATCH_SIZE]
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        all_embeddings.extend([item.embedding for item in response.data])

    return all_embeddings
