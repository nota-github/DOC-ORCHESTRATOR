"""CLI: Semantic search over indexed Confluence pages."""

import argparse
import json
import sys
from collections import defaultdict

from scripts.rag.config import TOP_K_CHUNKS, TOP_K_PAGES
from scripts.rag.embedder import embed_texts
from scripts.rag.store import VectorStore


def semantic_search(query: str, top_k: int = TOP_K_PAGES) -> dict:
    """Search the vector store and return top-k pages grouped by page_id.

    Returns:
        Dict with "results" key containing list of page matches.
    """
    store = VectorStore()
    query_embedding = embed_texts([query])[0]

    raw = store.query(query_embedding=query_embedding, top_k=TOP_K_CHUNKS)

    # Group by page_id, keep best score per page
    page_scores: dict[str, dict] = {}
    page_sections: dict[str, list[str]] = defaultdict(list)

    if raw["ids"] and raw["ids"][0]:
        for i, chunk_id in enumerate(raw["ids"][0]):
            meta = raw["metadatas"][0][i]
            distance = raw["distances"][0][i]
            score = 1 - distance  # cosine distance -> similarity

            page_id = meta["page_id"]
            section = meta.get("section_title", "")
            if section and section not in page_sections[page_id]:
                page_sections[page_id].append(section)

            if page_id not in page_scores or score > page_scores[page_id]["score"]:
                page_scores[page_id] = {
                    "page_id": page_id,
                    "title": meta["page_title"],
                    "url": meta["url"],
                    "score": score,
                }

    # Sort by score descending, take top-k
    sorted_pages = sorted(page_scores.values(), key=lambda x: x["score"], reverse=True)
    results = []
    for page in sorted_pages[:top_k]:
        page["matched_sections"] = page_sections.get(page["page_id"], [])
        results.append(page)

    return {"results": results}


def main() -> None:
    parser = argparse.ArgumentParser(description="Semantic search over Confluence pages.")
    parser.add_argument("--query", required=True, help="Search query text.")
    parser.add_argument("--top-k", type=int, default=TOP_K_PAGES, help="Number of pages to return.")
    args = parser.parse_args()

    result = semantic_search(query=args.query, top_k=args.top_k)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
