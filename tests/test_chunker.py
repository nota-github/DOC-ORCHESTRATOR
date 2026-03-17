"""Tests for the HTML chunker module."""

import pytest

from scripts.rag.chunker import Chunk, chunk_page, count_tokens, _clean_html, _extract_sections, _split_text
from scripts.rag.config import CHUNK_SIZE


class TestCountTokens:
    def test_empty_string(self):
        assert count_tokens("") == 0

    def test_basic_text(self):
        tokens = count_tokens("Hello, world!")
        assert tokens > 0

    def test_korean_text(self):
        tokens = count_tokens("모델 레지스트리 관련 주간 미팅입니다")
        assert tokens > 0


class TestCleanHtml:
    def test_removes_structured_macro(self):
        html = '<p>text</p><ac:structured-macro ac:name="code"><p>code</p></ac:structured-macro><p>more</p>'
        soup = _clean_html(html)
        assert "ac:structured-macro" not in str(soup)
        assert "text" in soup.get_text()
        assert "more" in soup.get_text()

    def test_removes_emoticon(self):
        html = '<p>hello <ac:emoticon ac:name="smile" /> world</p>'
        soup = _clean_html(html)
        assert "ac:emoticon" not in str(soup)
        assert "hello" in soup.get_text()

    def test_preserves_normal_html(self):
        html = "<h1>Title</h1><p>Content here</p>"
        soup = _clean_html(html)
        assert "Title" in soup.get_text()
        assert "Content here" in soup.get_text()


class TestExtractSections:
    def test_single_section_no_heading(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup("<p>Just some text</p>", "html.parser")
        sections = _extract_sections(soup)
        assert len(sections) == 1
        assert sections[0][0] == ""  # no title
        assert "Just some text" in sections[0][1]

    def test_multiple_headings(self):
        from bs4 import BeautifulSoup
        html = "<h1>Intro</h1><p>Intro text</p><h2>Details</h2><p>Detail text</p>"
        soup = BeautifulSoup(html, "html.parser")
        sections = _extract_sections(soup)
        assert len(sections) == 2
        assert sections[0][0] == "Intro"
        assert "Intro text" in sections[0][1]
        assert sections[1][0] == "Details"
        assert "Detail text" in sections[1][1]

    def test_empty_html(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup("", "html.parser")
        sections = _extract_sections(soup)
        assert len(sections) == 0


class TestSplitText:
    def test_short_text_no_split(self):
        text = "Short text"
        chunks = _split_text(text, max_tokens=100, overlap_tokens=10)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_splits(self):
        # Create text that exceeds token limit
        text = "word " * 500  # ~500 tokens
        chunks = _split_text(text, max_tokens=100, overlap_tokens=20)
        assert len(chunks) > 1
        # Each chunk should not exceed the limit (approximately)
        for chunk in chunks:
            assert count_tokens(chunk) <= 110  # small margin for boundary


class TestChunkPage:
    def test_basic_page(self):
        html = "<h1>Section A</h1><p>Content of section A.</p><h2>Section B</h2><p>Content of section B.</p>"
        chunks = chunk_page(
            page_id="12345",
            page_title="Test Page",
            body_html=html,
            url="https://example.com/page/12345",
        )
        assert len(chunks) == 2
        assert all(isinstance(c, Chunk) for c in chunks)
        assert chunks[0].page_id == "12345"
        assert chunks[0].page_title == "Test Page"
        assert chunks[0].section_title == "Section A"
        assert chunks[1].section_title == "Section B"

    def test_chunk_id_is_safe(self):
        html = "<h1>특수 문자 / 섹션!</h1><p>Content</p>"
        chunks = chunk_page("1", "Title", html, "http://x")
        for c in chunks:
            assert " " not in c.chunk_id
            assert "/" not in c.chunk_id

    def test_empty_html(self):
        chunks = chunk_page("1", "Empty", "", "http://x")
        assert len(chunks) == 0

    def test_confluence_macros_removed(self):
        html = '<p>Before</p><ac:structured-macro ac:name="toc"><ac:parameter ac:name="maxLevel">3</ac:parameter></ac:structured-macro><p>After</p>'
        chunks = chunk_page("1", "Macros", html, "http://x")
        full_text = " ".join(c.text for c in chunks)
        assert "Before" in full_text
        assert "After" in full_text
        assert "toc" not in full_text

    def test_token_limit_respected(self):
        # Create a page with a very long section
        long_text = "단어 " * 2000
        html = f"<h1>Long</h1><p>{long_text}</p>"
        chunks = chunk_page("1", "Long Page", html, "http://x")
        assert len(chunks) > 1
        for c in chunks:
            tokens = count_tokens(c.text)
            assert tokens <= CHUNK_SIZE + 50  # allow small overshoot at boundaries
