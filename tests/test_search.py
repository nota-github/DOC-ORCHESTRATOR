"""Tests for the semantic search module."""

from unittest.mock import patch, MagicMock

import pytest

from scripts.rag.search import semantic_search


@pytest.fixture
def mock_store_and_embedder():
    """Mock VectorStore and embed_texts for search tests."""
    mock_query_result = {
        "ids": [["c1_intro_0", "c2_intro_0", "c1_details_0", "c3_intro_0"]],
        "metadatas": [[
            {"page_id": "p1", "page_title": "Page One", "section_title": "Intro", "url": "http://x/p1"},
            {"page_id": "p2", "page_title": "Page Two", "section_title": "Intro", "url": "http://x/p2"},
            {"page_id": "p1", "page_title": "Page One", "section_title": "Details", "url": "http://x/p1"},
            {"page_id": "p3", "page_title": "Page Three", "section_title": "Intro", "url": "http://x/p3"},
        ]],
        "distances": [[0.1, 0.3, 0.2, 0.5]],  # cosine distances
    }

    with patch("scripts.rag.search.VectorStore") as MockStore, \
         patch("scripts.rag.search.embed_texts") as mock_embed:
        mock_instance = MagicMock()
        mock_instance.query.return_value = mock_query_result
        MockStore.return_value = mock_instance
        mock_embed.return_value = [[0.5, 0.5]]

        yield MockStore, mock_embed


class TestSemanticSearch:
    def test_returns_correct_format(self, mock_store_and_embedder):
        result = semantic_search("test query", top_k=3)
        assert "results" in result
        assert isinstance(result["results"], list)

    def test_groups_by_page_id(self, mock_store_and_embedder):
        result = semantic_search("test query", top_k=10)
        page_ids = [r["page_id"] for r in result["results"]]
        # p1 appears twice in chunks but should be grouped to one result
        assert page_ids.count("p1") == 1

    def test_sorted_by_score_descending(self, mock_store_and_embedder):
        result = semantic_search("test query", top_k=10)
        scores = [r["score"] for r in result["results"]]
        assert scores == sorted(scores, reverse=True)

    def test_best_score_per_page(self, mock_store_and_embedder):
        result = semantic_search("test query", top_k=10)
        p1 = next(r for r in result["results"] if r["page_id"] == "p1")
        # p1 has distances 0.1 and 0.2 → scores 0.9 and 0.8 → best is 0.9
        assert p1["score"] == pytest.approx(0.9)

    def test_matched_sections_collected(self, mock_store_and_embedder):
        result = semantic_search("test query", top_k=10)
        p1 = next(r for r in result["results"] if r["page_id"] == "p1")
        assert "Intro" in p1["matched_sections"]
        assert "Details" in p1["matched_sections"]

    def test_respects_top_k(self, mock_store_and_embedder):
        result = semantic_search("test query", top_k=2)
        assert len(result["results"]) <= 2

    def test_empty_results(self):
        with patch("scripts.rag.search.VectorStore") as MockStore, \
             patch("scripts.rag.search.embed_texts") as mock_embed:
            mock_instance = MagicMock()
            mock_instance.query.return_value = {"ids": [[]], "metadatas": [[]], "distances": [[]]}
            MockStore.return_value = mock_instance
            mock_embed.return_value = [[0.5, 0.5]]

            result = semantic_search("test query")
            assert result["results"] == []
