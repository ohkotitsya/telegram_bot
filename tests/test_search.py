"""Tests for ai/search.py — the web search pipeline.

All providers and the AI are mocked, so these tests never hit the network.
"""

from unittest.mock import MagicMock, patch

import pytest

from ai import search


@pytest.fixture
def mock_client():
    """Mock the Anthropic client used for classification and summarization."""
    fake = MagicMock()
    fake.messages.create.return_value = MagicMock(content=[MagicMock(type="text", text="CHAT")])
    with patch.object(search, "_client", fake):
        yield fake


def test_needs_web_returns_true_for_search(mock_client):
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(type="text", text="SEARCH")]
    )
    assert search.needs_web("what happened today") is True


def test_needs_web_returns_false_for_chat(mock_client):
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(type="text", text="CHAT")]
    )
    assert search.needs_web("hello how are you") is False


def test_needs_web_defaults_to_chat_on_error(mock_client):
    """If the classifier fails, we chat rather than search."""
    mock_client.messages.create.side_effect = RuntimeError("boom")
    assert search.needs_web("anything") is False


def test_search_web_returns_message_when_no_results(mock_client):
    """No provider results yields a friendly message, not an exception."""
    with (
        patch.object(search, "_ddg_text", return_value=[]),
        patch.object(search, "_ddg_news", return_value=[]),
        patch.object(search, "_wikipedia", return_value=[]),
    ):
        result = search.search_web("nothing here")

    assert "couldn't find" in result.lower()


def test_search_web_includes_sources(mock_client):
    """The answer is followed by a Sources block with links."""
    results = [
        {"title": "Example", "href": "https://example.com", "body": "Some snippet"},
    ]

    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(type="text", text="The answer is 42. [1]")]
    )

    with (
        patch.object(search, "_ddg_text", return_value=results),
        patch.object(search, "_ddg_news", return_value=[]),
        patch.object(search, "_wikipedia", return_value=[]),
    ):
        result = search.search_web("the answer")

    assert "Sources" in result
    assert "https://example.com" in result
    assert "42" in result


def test_search_web_falls_back_to_raw_results(mock_client):
    """If the AI summarization fails, raw results are returned instead."""
    results = [
        {"title": "Example", "href": "https://example.com", "body": "Raw snippet text"},
    ]
    mock_client.messages.create.side_effect = RuntimeError("AI down")

    with (
        patch.object(search, "_ddg_text", return_value=results),
        patch.object(search, "_ddg_news", return_value=[]),
        patch.object(search, "_wikipedia", return_value=[]),
    ):
        result = search.search_web("query")

    assert "https://example.com" in result
    assert "Raw snippet text" in result


def test_search_web_deduplicates_urls(mock_client):
    """The same URL from two providers is only counted once."""
    duplicate = {"title": "Same", "href": "https://same.com", "body": "x"}
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(type="text", text="answer")]
    )

    with (
        patch.object(search, "_ddg_text", return_value=[duplicate]),
        patch.object(search, "_ddg_news", return_value=[duplicate]),
        patch.object(search, "_wikipedia", return_value=[]),
    ):
        result = search.search_web("query")

    # One source link, not two
    assert result.count("https://same.com") == 1


def test_fetch_page_returns_empty_on_error():
    """A failed page fetch degrades to an empty string, never an exception."""
    import urllib.request

    with patch.object(urllib.request, "urlopen", side_effect=OSError("no network")):
        assert search._fetch_page("https://example.com") == ""
