"""Tests for the ChromaDB vector store wrapper."""

import tempfile

import pytest

from scripts.rag.store import VectorStore


@pytest.fixture
def temp_store(tmp_path):
    """Create a VectorStore with a temporary directory."""
    return VectorStore(path=str(tmp_path / "testdb"), collection_name="test_collection")


class TestVectorStore:
    def test_empty_stats(self, temp_store):
        stats = temp_store.get_stats()
        assert stats["collection_name"] == "test_collection"
        assert stats["count"] == 0

    def test_upsert_and_query(self, temp_store):
        # Create simple test data with 3-dim embeddings
        temp_store.upsert(
            ids=["chunk_1", "chunk_2", "chunk_3"],
            embeddings=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.9, 0.1, 0.0]],
            documents=["doc about cats", "doc about dogs", "doc about kittens"],
            metadatas=[
                {"page_id": "p1", "page_title": "Cats", "section_title": "Intro", "url": "http://x/1"},
                {"page_id": "p2", "page_title": "Dogs", "section_title": "Intro", "url": "http://x/2"},
                {"page_id": "p1", "page_title": "Cats", "section_title": "Details", "url": "http://x/1"},
            ],
        )

        assert temp_store.get_stats()["count"] == 3

        # Query for something similar to chunk_1
        results = temp_store.query(query_embedding=[0.95, 0.05, 0.0], top_k=2)
        assert len(results["ids"][0]) == 2
        # chunk_1 and chunk_3 should be closest (both in the cat/kitten direction)
        returned_ids = set(results["ids"][0])
        assert "chunk_1" in returned_ids or "chunk_3" in returned_ids

    def test_upsert_overwrites(self, temp_store):
        temp_store.upsert(
            ids=["c1"],
            embeddings=[[1.0, 0.0]],
            documents=["original"],
            metadatas=[{"page_id": "p1", "page_title": "T", "section_title": "", "url": "http://x"}],
        )
        temp_store.upsert(
            ids=["c1"],
            embeddings=[[0.0, 1.0]],
            documents=["updated"],
            metadatas=[{"page_id": "p1", "page_title": "T", "section_title": "", "url": "http://x"}],
        )
        assert temp_store.get_stats()["count"] == 1

    def test_delete_by_page_id(self, temp_store):
        temp_store.upsert(
            ids=["c1", "c2", "c3"],
            embeddings=[[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]],
            documents=["a", "b", "c"],
            metadatas=[
                {"page_id": "p1", "page_title": "T1", "section_title": "", "url": "http://x"},
                {"page_id": "p2", "page_title": "T2", "section_title": "", "url": "http://x"},
                {"page_id": "p1", "page_title": "T1", "section_title": "s2", "url": "http://x"},
            ],
        )
        assert temp_store.get_stats()["count"] == 3

        temp_store.delete_by_page_id("p1")
        assert temp_store.get_stats()["count"] == 1

    def test_query_returns_metadata(self, temp_store):
        temp_store.upsert(
            ids=["c1"],
            embeddings=[[1.0, 0.0]],
            documents=["test doc"],
            metadatas=[{"page_id": "p1", "page_title": "Title", "section_title": "Sec", "url": "http://test"}],
        )
        results = temp_store.query(query_embedding=[1.0, 0.0], top_k=1)
        assert results["metadatas"][0][0]["page_id"] == "p1"
        assert results["metadatas"][0][0]["page_title"] == "Title"
        assert results["documents"][0][0] == "test doc"
