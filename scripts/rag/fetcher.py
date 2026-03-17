"""Fetch all pages from a Confluence space."""

import os
import time
from datetime import datetime

from atlassian import Confluence

from scripts.rag.config import CONFLUENCE_SPACE


def _create_client(
    url: str | None = None,
    email: str | None = None,
    token: str | None = None,
) -> Confluence:
    return Confluence(
        url=url or os.environ["CONFLUENCE_URL"],
        username=email or os.environ["CONFLUENCE_EMAIL"],
        password=token or os.environ["CONFLUENCE_TOKEN"],
        cloud=True,
    )


def fetch_all_pages(
    space_key: str = CONFLUENCE_SPACE,
    url: str | None = None,
    email: str | None = None,
    token: str | None = None,
    modified_after: datetime | None = None,
) -> list[dict]:
    """Fetch all pages from the given Confluence space.

    Args:
        space_key: Confluence space key (default: NPP02).
        url: Confluence base URL (default: from env).
        email: User email (default: from env).
        token: API token (default: from env).
        modified_after: If set, only return pages modified after this time.

    Returns:
        List of dicts with page_id, title, body_html, url, last_modified.
    """
    confluence = _create_client(url, email, token)
    pages: list[dict] = []
    start = 0
    limit = 25
    max_retries = 5

    while True:
        retries = 0
        while retries < max_retries:
            try:
                results = confluence.get_all_pages_from_space(
                    space=space_key,
                    start=start,
                    limit=limit,
                    expand="body.storage,version",
                )
                break
            except Exception as e:
                retries += 1
                if retries >= max_retries:
                    raise
                wait = min(2 ** retries, 30)
                print(f"  Retry {retries}/{max_retries} after error: {e}. Waiting {wait}s...")
                time.sleep(wait)

        if not results:
            break

        for page in results:
            last_modified_str = page.get("version", {}).get("when", "")
            if modified_after and last_modified_str:
                page_modified = datetime.fromisoformat(
                    last_modified_str.replace("Z", "+00:00")
                )
                if page_modified <= modified_after.astimezone(page_modified.tzinfo):
                    continue

            base_url = (url or os.environ["CONFLUENCE_URL"]).rstrip("/")
            page_url = f"{base_url}/wiki/spaces/{space_key}/pages/{page['id']}"

            pages.append({
                "page_id": page["id"],
                "title": page["title"],
                "body_html": page.get("body", {}).get("storage", {}).get("value", ""),
                "url": page_url,
                "last_modified": last_modified_str,
            })

        if len(results) < limit:
            break
        start += limit

    return pages
