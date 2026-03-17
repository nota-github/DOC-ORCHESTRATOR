"""Tests for acceptance rate evaluation."""

import json

import pytest

from scripts.eval.acceptance_eval import evaluate_acceptance


class TestAcceptanceEval:
    def test_no_logs(self, tmp_path):
        result = evaluate_acceptance(str(tmp_path))
        assert result["total_proposals"] == 0
        assert result["acceptance_rate"] == 0.0
        assert "message" in result

    def test_single_log_all_applied(self, tmp_path):
        log = {
            "proposals": [
                {"status": "applied", "classification": "REQUIRED"},
                {"status": "applied", "classification": "RECOMMENDED"},
            ]
        }
        (tmp_path / "2026-03-01_update.json").write_text(json.dumps(log))

        result = evaluate_acceptance(str(tmp_path))
        assert result["total_proposals"] == 2
        assert result["applied"] == 2
        assert result["skipped"] == 0
        assert result["acceptance_rate"] == 1.0

    def test_mixed_statuses(self, tmp_path):
        log = {
            "proposals": [
                {"status": "applied", "classification": "REQUIRED"},
                {"status": "skipped", "classification": "REQUIRED"},
                {"status": "applied", "classification": "RECOMMENDED"},
                {"status": "skipped", "classification": "RECOMMENDED"},
                {"status": "skipped", "classification": "RECOMMENDED"},
            ]
        }
        (tmp_path / "2026-03-01_update.json").write_text(json.dumps(log))

        result = evaluate_acceptance(str(tmp_path))
        assert result["total_proposals"] == 5
        assert result["applied"] == 2
        assert result["skipped"] == 3
        assert result["acceptance_rate"] == pytest.approx(0.4)

        # Check per-classification breakdown
        assert result["by_classification"]["REQUIRED"]["total"] == 2
        assert result["by_classification"]["REQUIRED"]["applied"] == 1
        assert result["by_classification"]["REQUIRED"]["acceptance_rate"] == 0.5
        assert result["by_classification"]["RECOMMENDED"]["total"] == 3
        assert result["by_classification"]["RECOMMENDED"]["applied"] == 1

    def test_multiple_log_files(self, tmp_path):
        for i, status in enumerate(["applied", "skipped"]):
            log = {"proposals": [{"status": status, "classification": "REQUIRED"}]}
            (tmp_path / f"2026-03-0{i+1}_update.json").write_text(json.dumps(log))

        result = evaluate_acceptance(str(tmp_path))
        assert result["total_proposals"] == 2
        assert result["applied"] == 1
        assert result["acceptance_rate"] == 0.5

    def test_invalid_json_skipped(self, tmp_path):
        (tmp_path / "bad_update.json").write_text("not json")
        log = {"proposals": [{"status": "applied", "classification": "REQUIRED"}]}
        (tmp_path / "good_update.json").write_text(json.dumps(log))

        result = evaluate_acceptance(str(tmp_path))
        assert result["total_proposals"] == 1
