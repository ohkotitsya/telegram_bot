"""Tests for ai/client.py — conversation history handling.

The Anthropic API is mocked: these tests never make a network call.
"""

from unittest.mock import MagicMock, patch

import pytest

from ai import client


@pytest.fixture
def mock_client():
    """Replace the Anthropic client with a mock and yield it."""
    fake = MagicMock()
    fake.messages.create.return_value = MagicMock(
        content=[MagicMock(type="text", text="Hello from Claude")]
    )
    with patch.object(client, "_client", fake):
        yield fake


@pytest.fixture(autouse=True)
def _clear_history():
    """Each test starts with an empty conversation store."""
    client._conversations.clear()
    yield
    client._conversations.clear()


def test_ask_claude_returns_text(mock_client):
    reply = client.ask_claude(chat_id=1, user_message="Hi")

    assert reply == "Hello from Claude"
    mock_client.messages.create.assert_called_once()


def test_ask_claude_sends_user_message(mock_client):
    client.ask_claude(chat_id=42, user_message="What is Python?")

    kwargs = mock_client.messages.create.call_args.kwargs
    sent = kwargs["messages"]
    # The request carries the user turn plus any prior turns — the assistant
    # reply is appended to the store *after* the call returns.
    assert sent[-1] == {"role": "user", "content": "What is Python?"}
    assert kwargs["model"] == client.AI_MODEL
    assert kwargs["system"] == client.SYSTEM_PROMPT


def test_history_is_kept_per_chat(mock_client):
    client.ask_claude(chat_id=1, user_message="first")
    client.ask_claude(chat_id=2, user_message="second")

    assert len(client._conversations[1]) == 2  # user + assistant
    assert len(client._conversations[2]) == 2


def test_history_accumulates_across_turns(mock_client):
    client.ask_claude(chat_id=1, user_message="one")
    client.ask_claude(chat_id=1, user_message="two")

    history = client._conversations[1]
    assert history[0] == {"role": "user", "content": "one"}
    assert history[1] == {"role": "assistant", "content": "Hello from Claude"}
    assert history[2] == {"role": "user", "content": "two"}


def test_history_is_trimmed_to_limit(mock_client):
    """Old messages are dropped once the history exceeds the cap."""
    limit = client.MAX_HISTORY * 2
    for i in range(limit + 5):
        client.ask_claude(chat_id=1, user_message=f"msg-{i}")

    assert len(client._conversations[1]) <= limit


def test_clear_history_removes_conversation(mock_client):
    client.ask_claude(chat_id=1, user_message="remember this")
    assert 1 in client._conversations

    client.clear_history(1)
    assert 1 not in client._conversations


def test_clear_history_on_unknown_chat_is_safe(mock_client):
    """Clearing a chat that never existed must not raise."""
    client.clear_history(999)


def test_empty_response_falls_back_to_placeholder(mock_client):
    """A response with no text block yields a readable placeholder."""
    mock_client.messages.create.return_value = MagicMock(content=[])

    reply = client.ask_claude(chat_id=1, user_message="hi")

    assert reply
