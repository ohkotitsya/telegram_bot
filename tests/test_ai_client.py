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


def test_payment_error_is_explained():
    """A 402 from the provider gets a message that names the likely cause."""
    import anthropic
    import httpx

    from handlers.messages import build_reply

    request = httpx.Request("POST", "https://example.com/v1/messages")
    response = httpx.Response(
        402,
        json={"error": {"message": "This model requires an opencode API key"}},
        request=request,
    )
    error = anthropic.APIStatusError(
        "premium_model_requires_key",
        response=response,
        body={"error": {"message": "This model requires an opencode API key"}},
    )

    with patch.object(client, "_client") as mock:
        mock.messages.create.side_effect = error
        reply = build_reply(1, "hello", MagicMock(chat_data={}), force_direct=True)

    assert "402" in reply
    assert "ANTHROPIC_API_KEY" in reply


# ---------------------------------------------------------------------------
# Tool-output blocks (the provider may attach a memory/skill tool)
# ---------------------------------------------------------------------------
def _text_block(text):
    return MagicMock(type="text", text=text)


def _response(*blocks):
    return MagicMock(content=list(blocks))


SKILL_BLOCK = '[Skill result: memory_search]\n{"success":true,"data":{"memories":[],"count":0}}'


def test_extract_text_drops_tool_output_blocks():
    """The tool output arrives as a text block and must not reach the user."""
    response = _response(_text_block(SKILL_BLOCK), _text_block("Here is your answer."))

    assert client.extract_text(response) == "Here is your answer."


def test_extract_text_keeps_the_plain_answer():
    response = _response(_text_block("Just the answer."))

    assert client.extract_text(response) == "Just the answer."


def test_extract_text_ignores_thinking_blocks():
    thinking = MagicMock(type="thinking", thinking="Let me think...")
    response = _response(thinking, _text_block("Answer"))

    assert client.extract_text(response) == "Answer"


def test_reply_has_no_tool_output(mock_client):
    """A reply that only holds tool output never reaches the user."""
    mock_client.messages.create.return_value = _response(_text_block(SKILL_BLOCK))

    reply = client.ask_claude(chat_id=1, user_message="hi")

    assert SKILL_BLOCK not in reply
    assert "Skill result" not in reply


def test_reply_keeps_the_answer_next_to_tool_output(mock_client):
    """Tool output is dropped, the real answer is kept."""
    mock_client.messages.create.return_value = _response(
        _text_block(SKILL_BLOCK), _text_block("Claro! Aqui vai o codigo.")
    )

    reply = client.ask_claude(chat_id=1, user_message="codigo de calculadora")

    assert reply == "Claro! Aqui vai o codigo."
    assert "Skill result" not in reply


def test_tool_output_only_reply_is_retried(mock_client):
    """When the model answers with tool output only, the call is retried."""
    mock_client.messages.create.side_effect = [
        _response(_text_block(SKILL_BLOCK)),
        _response(_text_block("A resposta real.")),
    ]

    reply = client.ask_claude(chat_id=1, user_message="hi")

    assert reply == "A resposta real."
    assert mock_client.messages.create.call_count == 2


def test_tool_output_is_not_stored_in_the_history(mock_client):
    """Only the clean answer goes into the conversation history."""
    mock_client.messages.create.return_value = _response(
        _text_block(SKILL_BLOCK), _text_block("Resposta limpa.")
    )

    client.ask_claude(chat_id=1, user_message="hi")

    stored = client._conversations[1]
    assert all("Skill result" not in m["content"] for m in stored)
    assert stored[-1] == {"role": "assistant", "content": "Resposta limpa."}
