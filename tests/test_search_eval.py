"""Tests for search evaluation metrics."""

from unittest.mock import patch, MagicMock

import pytest

from scripts.eval.search_eval import compare_searches


class TestCompareSearches:
    @patch("scripts.eval.search_eval.semantic_search")
    @patch("scripts.eval.search_eval._keyword_search")
    def test_full_overlap(self, mock_kw, mock_rag):
        mock_kw.return_value = [
            {"page_id": "1", "title": "A"},
            {"page_id": "2", "title": "B"},
        ]
        mock_rag.return_value = {
            "results": [
                {"page_id": "1", "title": "A", "score": 0.9},
                {"page_id": "2", "title": "B", "score": 0.8},
            ]
        }

        result = compare_searches(["kw1"], "summary")
        assert result["keyword_count"] == 2
        assert result["rag_count"] == 2
        assert result["overlap_count"] == 2
        assert result["keyword_only_count"] == 0
        assert result["rag_only_count"] == 0
        assert result["jaccard_similarity"] == 1.0

    @patch("scripts.eval.search_eval.semantic_search")
    @patch("scripts.eval.search_eval._keyword_search")
    def test_no_overlap(self, mock_kw, mock_rag):
        mock_kw.return_value = [{"page_id": "1", "title": "A"}]
        mock_rag.return_value = {
            "results": [{"page_id": "2", "title": "B", "score": 0.9}]
        }

        result = compare_searches(["kw1"], "summary")
        assert result["overlap_count"] == 0
        assert result["keyword_only_count"] == 1
        assert result["rag_only_count"] == 1
        assert result["jaccard_similarity"] == 0.0

    @patch("scripts.eval.search_eval.semantic_search")
    @patch("scripts.eval.search_eval._keyword_search")
    def test_partial_overlap(self, mock_kw, mock_rag):
        mock_kw.return_value = [
            {"page_id": "1", "title": "A"},
            {"page_id": "2", "title": "B"},
        ]
        mock_rag.return_value = {
            "results": [
                {"page_id": "2", "title": "B", "score": 0.9},
                {"page_id": "3", "title": "C", "score": 0.8},
            ]
        }

        result = compare_searches(["kw1"], "summary")
        assert result["overlap_count"] == 1
        assert result["keyword_only_count"] == 1
        assert result["rag_only_count"] == 1
        # Jaccard: 1/3 = 0.3333
        assert result["jaccard_similarity"] == pytest.approx(0.3333, abs=0.001)

    @patch("scripts.eval.search_eval.semantic_search")
    @patch("scripts.eval.search_eval._keyword_search")
    def test_empty_results(self, mock_kw, mock_rag):
        mock_kw.return_value = []
        mock_rag.return_value = {"results": []}

        result = compare_searches(["kw1"], "summary")
        assert result["jaccard_similarity"] == 0.0
        assert result["union_count"] == 0
