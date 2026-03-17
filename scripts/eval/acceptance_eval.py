"""Acceptance rate evaluation from update logs."""

import json
from pathlib import Path


def evaluate_acceptance(logs_dir: str = "logs") -> dict:
    """Parse update logs and compute acceptance metrics.

    Looks for *_update.json files in the logs directory.
    Returns metrics on proposal acceptance rates.
    """
    log_path = Path(logs_dir)
    update_files = sorted(log_path.glob("*_update.json"))

    if not update_files:
        return {
            "total_proposals": 0,
            "applied": 0,
            "skipped": 0,
            "acceptance_rate": 0.0,
            "by_classification": {},
            "message": "No update logs found. Metrics will accumulate as the system is used.",
        }

    total = 0
    applied = 0
    skipped = 0
    by_class: dict[str, dict[str, int]] = {}

    for f in update_files:
        try:
            data = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        proposals = data.get("proposals", [])
        for p in proposals:
            total += 1
            status = p.get("status", "unknown")
            classification = p.get("classification", "UNKNOWN")

            if classification not in by_class:
                by_class[classification] = {"applied": 0, "skipped": 0, "total": 0}
            by_class[classification]["total"] += 1

            if status == "applied":
                applied += 1
                by_class[classification]["applied"] += 1
            else:
                skipped += 1
                by_class[classification]["skipped"] += 1

    # Compute rates
    for cls_data in by_class.values():
        cls_data["acceptance_rate"] = round(
            cls_data["applied"] / cls_data["total"], 4
        ) if cls_data["total"] > 0 else 0.0

    return {
        "total_proposals": total,
        "applied": applied,
        "skipped": skipped,
        "acceptance_rate": round(applied / total, 4) if total > 0 else 0.0,
        "by_classification": by_class,
    }
