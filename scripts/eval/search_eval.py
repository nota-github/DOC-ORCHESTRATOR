"""Keyword vs RAG search comparison evaluation."""

import json
import os

from atlassian import Confluence

from scripts.rag.config import CONFLUENCE_SPACE
from scripts.rag.search import semantic_search


def _keyword_search(keywords: list[str], space_key: str = CONFLUENCE_SPACE) -> list[dict]:
    """Run keyword search via Confluence REST API."""
    confluence = Confluence(
        url=os.environ["CONFLUENCE_URL"],
        username=os.environ["CONFLUENCE_EMAIL"],
        password=os.environ["CONFLUENCE_API_TOKEN"],
        cloud=True,
    )

    seen_ids: set[str] = set()
    results: list[dict] = []

    for kw in keywords:
        cql = f'space = "{space_key}" AND text ~ "{kw}"'
        try:
            resp = confluence.cql(cql, limit=20)
        except Exception:
            continue

        for item in resp.get("results", []):
            content = item.get("content", item)
            page_id = str(content.get("id", ""))
            if page_id and page_id not in seen_ids:
                seen_ids.add(page_id)
                results.append({
                    "page_id": page_id,
                    "title": content.get("title", ""),
                })

    return results


def compare_searches(
    keywords: list[str],
    summary: str,
    top_k: int = 15,
) -> dict:
    """Compare keyword search vs RAG search results.

    Returns metrics: overlap, unique counts, Jaccard similarity.
    """
    # Keyword search
    kw_results = _keyword_search(keywords)
    kw_ids = {r["page_id"] for r in kw_results}

    # RAG search
    query = ". ".join(keywords) + ". " + summary
    rag_output = semantic_search(query=query, top_k=top_k)
    rag_ids = {r["page_id"] for r in rag_output["results"]}

    intersection = kw_ids & rag_ids
    union = kw_ids | rag_ids

    jaccard = len(intersection) / len(union) if union else 0.0

    return {
        "keyword_count": len(kw_ids),
        "rag_count": len(rag_ids),
        "overlap_count": len(intersection),
        "keyword_only_count": len(kw_ids - rag_ids),
        "rag_only_count": len(rag_ids - kw_ids),
        "union_count": len(union),
        "jaccard_similarity": round(jaccard, 4),
        "overlap_ids": sorted(intersection),
        "keyword_only_ids": sorted(kw_ids - rag_ids),
        "rag_only_ids": sorted(rag_ids - kw_ids),
    }
