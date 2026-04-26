#!/usr/bin/env python3
"""
Confluence Helper MCP Server

Provides additional Confluence tools not available in mcp-atlassian:
- confluence_get_history: Get version history for a page
- confluence_restore_version: Restore a page to a previous version
- confluence_patch_section: Update only a specific section of a page

Usage:
    Add to your .mcp.json:
    {
        "mcpServers": {
            "confluence-helper": {
                "command": "python",
                "args": ["scripts/helper_mcp.py"]
            }
        }
    }

Environment variables required:
    CONFLUENCE_URL: Base URL (e.g., https://your-domain.atlassian.net)
    CONFLUENCE_EMAIL: Your Atlassian account email
    CONFLUENCE_TOKEN: Your Atlassian API token
"""

import os
import re
import json
from typing import Optional
from mcp.server.fastmcp import FastMCP
from atlassian import Confluence

# Initialize MCP server
mcp = FastMCP("confluence-helper")

# Confluence client (lazy initialization)
_confluence_client: Optional[Confluence] = None


def get_confluence() -> Confluence:
    """Get or create Confluence client."""
    global _confluence_client
    if _confluence_client is None:
        url = os.environ.get("CONFLUENCE_URL")
        if not url:
            raise ValueError("CONFLUENCE_URL environment variable must be set")
        email = os.environ.get("CONFLUENCE_EMAIL")
        token = os.environ.get("CONFLUENCE_TOKEN")

        if not email or not token:
            raise ValueError(
                "Missing required environment variables: "
                "CONFLUENCE_EMAIL and CONFLUENCE_TOKEN must be set"
            )

        _confluence_client = Confluence(
            url=url,
            username=email,
            password=token,
            cloud=True
        )
    return _confluence_client


@mcp.tool()
def confluence_get_history(page_id: str, limit: int = 25) -> str:
    """
    Get version history for a Confluence page.

    Args:
        page_id: The Confluence page ID
        limit: Maximum number of versions to return (default: 25)

    Returns:
        JSON string with version history including version number,
        update time, and author for each version
    """
    confluence = get_confluence()

    # Get page history using the REST API
    # The atlassian library doesn't have a direct method, so we use the underlying request
    response = confluence.get(
        f"rest/api/content/{page_id}/history",
        params={"expand": "lastUpdated,previousVersion,contributors.publishers.users"}
    )

    # Also get the version list with more details
    versions_response = confluence.get(
        f"rest/api/content/{page_id}/version",
        params={"limit": limit, "expand": "content"}
    )

    versions = []
    for v in versions_response.get("results", []):
        versions.append({
            "version": v.get("number"),
            "when": v.get("when"),
            "message": v.get("message", ""),
            "author": v.get("by", {}).get("displayName", "Unknown"),
            "email": v.get("by", {}).get("email", "")
        })

    result = {
        "page_id": page_id,
        "current_version": response.get("lastUpdated", {}).get("number"),
        "created": response.get("createdDate"),
        "versions": versions
    }

    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def confluence_get_version_content(page_id: str, version: int) -> str:
    """
    Get the content of a specific version of a Confluence page.

    Args:
        page_id: The Confluence page ID
        version: The version number to retrieve

    Returns:
        JSON string with page content at the specified version
    """
    confluence = get_confluence()

    response = confluence.get(
        f"rest/api/content/{page_id}",
        params={
            "version": version,
            "expand": "body.storage,version"
        }
    )

    result = {
        "page_id": page_id,
        "title": response.get("title"),
        "version": response.get("version", {}).get("number"),
        "content": response.get("body", {}).get("storage", {}).get("value", "")
    }

    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def confluence_restore_version(page_id: str, version: int, message: str = "") -> str:
    """
    Restore a Confluence page to a previous version.

    This creates a new version with the content from the specified old version.

    Args:
        page_id: The Confluence page ID
        version: The version number to restore to
        message: Optional version message/comment

    Returns:
        JSON string with the result of the restore operation
    """
    confluence = get_confluence()

    # Step 1: Get the old version's content
    old_version = confluence.get(
        f"rest/api/content/{page_id}",
        params={
            "version": version,
            "expand": "body.storage"
        }
    )

    old_content = old_version.get("body", {}).get("storage", {}).get("value", "")
    old_title = old_version.get("title")

    if not old_content:
        return json.dumps({
            "success": False,
            "error": f"Could not retrieve content for version {version}"
        })

    # Step 2: Get current version number
    current = confluence.get_page_by_id(page_id, expand="version")
    current_version = current.get("version", {}).get("number", 0)

    # Step 3: Update with old content
    restore_message = message or f"Restored to version {version}"

    result = confluence.update_page(
        page_id=page_id,
        title=old_title,
        body=old_content,
        type="page",
        representation="storage",
        version_comment=restore_message
    )

    return json.dumps({
        "success": True,
        "page_id": page_id,
        "restored_from_version": version,
        "new_version": current_version + 1,
        "message": restore_message,
        "url": f"{confluence.url}/wiki/spaces/{result.get('space', {}).get('key', '')}/pages/{page_id}"
    }, indent=2, ensure_ascii=False)


@mcp.tool()
def confluence_patch_section(
    page_id: str,
    section_title: str,
    new_content: str,
    version_comment: str = ""
) -> str:
    """
    Update only a specific section of a Confluence page, preserving all other content.

    The section is identified by its heading text (h1, h2, h3, etc.).
    Only the content between the specified heading and the next same-level heading
    (or end of document) will be replaced.

    Args:
        page_id: The Confluence page ID
        section_title: The heading text that identifies the section (e.g., "Action items")
        new_content: The new HTML content to replace the section body with
                    (do not include the heading itself, just the content)
        version_comment: Optional comment for the version history

    Returns:
        JSON string with the result of the update operation
    """
    confluence = get_confluence()

    # Get current page content in storage format
    page = confluence.get_page_by_id(
        page_id,
        expand="body.storage,version,space"
    )

    current_content = page.get("body", {}).get("storage", {}).get("value", "")
    current_version = page.get("version", {}).get("number", 0)
    title = page.get("title")
    space_key = page.get("space", {}).get("key", "")

    # Find the section by looking for heading tags with the section title
    # Confluence uses <h2>, <h3>, etc. with possible attributes
    # Pattern: find <h2...>...section_title...</h2> and content until next <h2

    # Escape special regex characters in section title
    escaped_title = re.escape(section_title)

    # Pattern to match the section heading and its content
    # This handles h1-h6 tags with any attributes
    pattern = re.compile(
        rf'(<h([1-6])[^>]*>(?:<[^>]+>)*\s*{escaped_title}\s*(?:<[^>]+>)*</h\2>)'  # Capture the heading
        rf'(.*?)'  # Capture content (non-greedy)
        rf'(?=<h[1-6]|$)',  # Until next heading or end
        re.DOTALL | re.IGNORECASE
    )

    match = pattern.search(current_content)

    if not match:
        # Try a simpler pattern for emoji-prefixed headings
        pattern_simple = re.compile(
            rf'(<h([1-6])[^>]*>.*?{escaped_title}.*?</h\2>)'
            rf'(.*?)'
            rf'(?=<h[1-6][^>]*>|$)',
            re.DOTALL | re.IGNORECASE
        )
        match = pattern_simple.search(current_content)

    if not match:
        return json.dumps({
            "success": False,
            "error": f"Could not find section with title '{section_title}'",
            "hint": "Make sure the section title matches exactly (case-insensitive)"
        }, indent=2, ensure_ascii=False)

    # Reconstruct the content with the new section
    heading = match.group(1)
    before_section = current_content[:match.start()]
    after_section = current_content[match.end():]

    # Build new content: everything before + heading + new content + everything after
    updated_content = before_section + heading + new_content + after_section

    # Update the page
    comment = version_comment or f"Updated section: {section_title}"

    result = confluence.update_page(
        page_id=page_id,
        title=title,
        body=updated_content,
        type="page",
        representation="storage",
        version_comment=comment
    )

    return json.dumps({
        "success": True,
        "page_id": page_id,
        "section_updated": section_title,
        "previous_version": current_version,
        "new_version": current_version + 1,
        "message": comment,
        "url": f"{confluence.url}/wiki/spaces/{space_key}/pages/{page_id}"
    }, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
