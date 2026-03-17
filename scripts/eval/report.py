"""Generate JSON and Markdown evaluation reports."""

import json
from datetime import datetime
from pathlib import Path


def generate_report(
    search_eval: dict | None = None,
    acceptance_eval: dict | None = None,
    output_dir: str = "logs",
) -> tuple[str, str]:
    """Generate evaluation report in JSON and Markdown formats.

    Returns (json_path, md_path).
    """
    timestamp = datetime.now().strftime("%Y-%m-%d")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    report = {
        "generated_at": datetime.now().isoformat(),
        "search_comparison": search_eval,
        "acceptance": acceptance_eval,
    }

    json_path = out / f"evaluation_report_{timestamp}.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))

    md_lines = [
        f"# Evaluation Report ({timestamp})",
        "",
    ]

    if search_eval:
        md_lines.extend([
            "## Search Comparison (Keyword vs RAG)",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
        ])
        for meeting in search_eval.get("meetings", [search_eval]):
            if "meeting_id" in meeting:
                md_lines.append(f"| **Meeting** | {meeting['meeting_id']} |")
            md_lines.extend([
                f"| Keyword results | {meeting.get('keyword_count', 'N/A')} |",
                f"| RAG results | {meeting.get('rag_count', 'N/A')} |",
                f"| Overlap | {meeting.get('overlap_count', 'N/A')} |",
                f"| Keyword-only | {meeting.get('keyword_only_count', 'N/A')} |",
                f"| RAG-only | {meeting.get('rag_only_count', 'N/A')} |",
                f"| Jaccard similarity | {meeting.get('jaccard_similarity', 'N/A')} |",
                "",
            ])

    if acceptance_eval:
        md_lines.extend([
            "## Acceptance Rate",
            "",
            f"- Total proposals: {acceptance_eval.get('total_proposals', 0)}",
            f"- Applied: {acceptance_eval.get('applied', 0)}",
            f"- Skipped: {acceptance_eval.get('skipped', 0)}",
            f"- Acceptance rate: {acceptance_eval.get('acceptance_rate', 0.0):.1%}",
            "",
        ])
        by_class = acceptance_eval.get("by_classification", {})
        if by_class:
            md_lines.extend([
                "### By Classification",
                "",
                "| Classification | Total | Applied | Skipped | Rate |",
                "|---------------|-------|---------|---------|------|",
            ])
            for cls, d in by_class.items():
                rate = f"{d.get('acceptance_rate', 0):.1%}"
                md_lines.append(
                    f"| {cls} | {d['total']} | {d['applied']} | {d['skipped']} | {rate} |"
                )
            md_lines.append("")

    md_path = out / f"evaluation_report_{timestamp}.md"
    md_path.write_text("\n".join(md_lines))

    return str(json_path), str(md_path)
