"""ChromaDB vector store wrapper."""

from pathlib import Path

import chromadb

from scripts.rag.config import COLLECTION_NAME, TOP_K_CHUNKS, VECTORDB_PATH


class VectorStore:
    """Persistent ChromaDB store for Confluence page chunks."""

    def __init__(self, path: str | None = None, collection_name: str | None = None):
        db_path = path or VECTORDB_PATH
        Path(db_path).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=db_path)
        self._collection = self._client.get_or_create_collection(
            name=collection_name or COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        """Upsert chunks into the collection."""
        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def query(
        self,
        query_embedding: list[float],
        top_k: int = TOP_K_CHUNKS,
    ) -> dict:
        """Query the collection by embedding vector."""
        return self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

    def delete_by_page_id(self, page_id: str) -> None:
        """Delete all chunks belonging to a specific page."""
        self._collection.delete(where={"page_id": page_id})

    def get_stats(self) -> dict:
        """Return collection statistics."""
        return {
            "collection_name": self._collection.name,
            "count": self._collection.count(),
        }
