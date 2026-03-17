"""CLI: Build or update the vector index from Confluence pages."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.rag.chunker import chunk_page
from scripts.rag.config import VECTORDB_PATH
from scripts.rag.embedder import embed_texts
from scripts.rag.fetcher import fetch_all_pages
from scripts.rag.store import VectorStore

LAST_INDEXED_PATH = Path(VECTORDB_PATH) / ".last_indexed"


def _load_last_indexed() -> datetime | None:
    if LAST_INDEXED_PATH.exists():
        ts = LAST_INDEXED_PATH.read_text().strip()
        return datetime.fromisoformat(ts)
    return None


def _save_last_indexed(dt: datetime) -> None:
    LAST_INDEXED_PATH.parent.mkdir(parents=True, exist_ok=True)
    LAST_INDEXED_PATH.write_text(dt.isoformat())


def build_index(incremental: bool = False) -> None:
    """Build or incrementally update the vector index."""
    modified_after = None
    if incremental:
        modified_after = _load_last_indexed()
        if modified_after:
            print(f"Incremental mode: fetching pages modified after {modified_after.isoformat()}")
        else:
            print("No previous index found. Running full build.")

    print("Fetching pages from Confluence...")
    pages = fetch_all_pages(modified_after=modified_after)
    print(f"  Fetched {len(pages)} page(s)")

    if not pages:
        print("No pages to index.")
        return

    store = VectorStore()

    if incremental:
        for page in pages:
            store.delete_by_page_id(page["page_id"])

    print("Chunking pages...")
    all_chunks = []
    for page in pages:
        chunks = chunk_page(
            page_id=page["page_id"],
            page_title=page["title"],
            body_html=page["body_html"],
            url=page["url"],
        )
        all_chunks.extend(chunks)
    print(f"  Generated {len(all_chunks)} chunk(s)")

    if not all_chunks:
        print("No chunks generated.")
        return

    print("Generating embeddings...")
    texts = [c.text for c in all_chunks]
    embeddings = embed_texts(texts)
    print(f"  Generated {len(embeddings)} embedding(s)")

    print("Upserting into vector store...")
    store.upsert(
        ids=[c.chunk_id for c in all_chunks],
        embeddings=embeddings,
        documents=texts,
        metadatas=[
            {
                "page_id": c.page_id,
                "page_title": c.page_title,
                "section_title": c.section_title,
                "url": c.url,
            }
            for c in all_chunks
        ],
    )

    _save_last_indexed(datetime.now(timezone.utc))

    stats = store.get_stats()
    print(f"Done. Collection '{stats['collection_name']}' has {stats['count']} chunk(s).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build RAG vector index from Confluence.")
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Only index pages modified since last run.",
    )
    args = parser.parse_args()
    build_index(incremental=args.incremental)


if __name__ == "__main__":
    main()
