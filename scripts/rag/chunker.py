"""HTML to text chunk splitter for Confluence pages."""

import re
from dataclasses import dataclass

import tiktoken
from bs4 import BeautifulSoup, NavigableString, Tag

from scripts.rag.config import CHUNK_OVERLAP, CHUNK_SIZE


@dataclass
class Chunk:
    chunk_id: str
    page_id: str
    page_title: str
    section_title: str
    text: str
    url: str


_encoder = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_encoder.encode(text))


def _clean_html(html: str) -> BeautifulSoup:
    """Parse HTML and remove Confluence macros."""
    soup = BeautifulSoup(html, "html.parser")
    for macro in soup.find_all("ac:structured-macro"):
        macro.decompose()
    for emoticon in soup.find_all("ac:emoticon"):
        emoticon.decompose()
    return soup


def _extract_sections(soup: BeautifulSoup) -> list[tuple[str, str]]:
    """Split HTML into (section_title, text) pairs based on headings."""
    sections: list[tuple[str, str]] = []
    current_title = ""
    current_parts: list[str] = []

    for element in soup.children:
        if isinstance(element, Tag) and element.name in (
            "h1", "h2", "h3", "h4", "h5", "h6",
        ):
            if current_parts:
                text = " ".join(current_parts).strip()
                if text:
                    sections.append((current_title, text))
            current_title = element.get_text(strip=True)
            current_parts = []
        else:
            text = element.get_text(strip=True) if isinstance(element, Tag) else str(element).strip()
            if text:
                current_parts.append(text)

    if current_parts:
        text = " ".join(current_parts).strip()
        if text:
            sections.append((current_title, text))

    if not sections:
        full_text = soup.get_text(separator=" ", strip=True)
        if full_text:
            sections.append(("", full_text))

    return sections


def _split_text(text: str, max_tokens: int, overlap_tokens: int) -> list[str]:
    """Split text into chunks respecting token limits."""
    tokens = _encoder.encode(text)
    if len(tokens) <= max_tokens:
        return [text]

    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk_tokens = tokens[start:end]
        chunks.append(_encoder.decode(chunk_tokens))
        if end >= len(tokens):
            break
        start = end - overlap_tokens

    return chunks


def chunk_page(
    page_id: str,
    page_title: str,
    body_html: str,
    url: str,
) -> list[Chunk]:
    """Convert a Confluence page HTML body into text chunks."""
    soup = _clean_html(body_html)
    sections = _extract_sections(soup)

    chunks = []
    for section_title, text in sections:
        sub_texts = _split_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
        for i, sub_text in enumerate(sub_texts):
            chunk_id = f"{page_id}_{section_title or 'root'}_{i}"
            chunk_id = re.sub(r"[^a-zA-Z0-9_]", "_", chunk_id)
            chunks.append(Chunk(
                chunk_id=chunk_id,
                page_id=page_id,
                page_title=page_title,
                section_title=section_title,
                text=sub_text,
                url=url,
            ))

    return chunks
