"""Main evaluation CLI entry point."""

import argparse
import json
import sys
from pathlib import Path

from scripts.eval.acceptance_eval import evaluate_acceptance
from scripts.eval.llm_judge import evaluate_search_results
from scripts.eval.report import generate_report
from scripts.eval.search_eval import compare_searches


def _load_meetings(meetings_dir: str = "test-data/sample_meetings") -> list[dict]:
    """Load synthetic meeting transcripts."""
    meetings = []
    for f in sorted(Path(meetings_dir).glob("*.json")):
        try:
            data = json.loads(f.read_text())
            data["_file"] = f.name
            meetings.append(data)
        except (json.JSONDecodeError, OSError):
            print(f"Warning: could not load {f}", file=sys.stderr)
    return meetings


def run_search_eval(meetings: list[dict]) -> dict:
    """Run keyword vs RAG search comparison across all meetings."""
    results = []
    for m in meetings:
        keywords = m.get("keywords", [])
        summary = m.get("summary", m.get("transcript", "")[:500])
        meeting_id = m.get("_file", "unknown")

        print(f"  Evaluating search for: {meeting_id}")
        comparison = compare_searches(keywords=keywords, summary=summary)
        comparison["meeting_id"] = meeting_id
        results.append(comparison)

    # Compute aggregates
    if results:
        avg_jaccard = sum(r["jaccard_similarity"] for r in results) / len(results)
        avg_rag_only = sum(r["rag_only_count"] for r in results) / len(results)
    else:
        avg_jaccard = 0.0
        avg_rag_only = 0.0

    return {
        "meetings": results,
        "aggregate": {
            "avg_jaccard_similarity": round(avg_jaccard, 4),
            "avg_rag_unique_documents": round(avg_rag_only, 2),
            "num_meetings": len(results),
        },
    }


def run_acceptance_eval() -> dict:
    """Run acceptance rate evaluation."""
    return evaluate_acceptance()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run DOC-ORCHESTRATOR evaluations.")
    parser.add_argument("--search-only", action="store_true", help="Only run search comparison.")
    parser.add_argument("--acceptance-only", action="store_true", help="Only run acceptance eval.")
    parser.add_argument("--meetings-dir", default="test-data/sample_meetings")
    args = parser.parse_args()

    search_result = None
    acceptance_result = None

    if not args.acceptance_only:
        print("Running search comparison evaluation...")
        meetings = _load_meetings(args.meetings_dir)
        if not meetings:
            print("No meeting files found. Skipping search eval.")
        else:
            search_result = run_search_eval(meetings)
            print(f"  Completed: {search_result['aggregate']['num_meetings']} meeting(s)")

    if not args.search_only:
        print("Running acceptance evaluation...")
        acceptance_result = run_acceptance_eval()
        print(f"  Total proposals: {acceptance_result['total_proposals']}")

    json_path, md_path = generate_report(
        search_eval=search_result,
        acceptance_eval=acceptance_result,
    )
    print(f"\nReports generated:")
    print(f"  JSON: {json_path}")
    print(f"  Markdown: {md_path}")


if __name__ == "__main__":
    main()
