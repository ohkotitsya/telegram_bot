"""Tests for direct chat mode — the /chat command."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from handlers.chat_mode import (
    DIRECT_CHAT_KEY,
    is_direct_chat,
    set_direct_chat,
    toggle_direct_chat,
)


@pytest.fixture
def fake_update():
    update = MagicMock()
    update.effective_chat.id = 12345
    update.message.text = "hello"
    update.message.reply_text = AsyncMock()
    update.message.chat.send_action = AsyncMock()
    return update


@pytest.fixture
def fake_context():
    """A context with real (empty) chat_data, like Telegram's."""
    context = MagicMock()
    context.args = []
    context.chat_data = {}
    return context


# ---------------------------------------------------------------------------
# The mode helpers
# ---------------------------------------------------------------------------
def test_direct_chat_is_off_by_default(fake_context):
    assert is_direct_chat(fake_context) is False


def test_set_direct_chat_enables(fake_context):
    set_direct_chat(fake_context, True)
    assert is_direct_chat(fake_context) is True


def test_set_direct_chat_disables(fake_context):
    set_direct_chat(fake_context, True)
    set_direct_chat(fake_context, False)
    assert is_direct_chat(fake_context) is False


def test_toggle_flips_state(fake_context):
    assert toggle_direct_chat(fake_context) is True
    assert is_direct_chat(fake_context) is True
    assert toggle_direct_chat(fake_context) is False
    assert is_direct_chat(fake_context) is False


def test_mode_is_stored_in_chat_data(fake_context):
    set_direct_chat(fake_context, True)
    assert fake_context.chat_data[DIRECT_CHAT_KEY] is True


# ---------------------------------------------------------------------------
# The /chat command
# ---------------------------------------------------------------------------
async def test_chat_toggles_on(fake_update, fake_context):
    from handlers import cmd_chat

    await cmd_chat(fake_update, fake_context)

    assert is_direct_chat(fake_context) is True
    reply = fake_update.message.reply_text.await_args.args[0]
    assert "Direct chat on" in reply


async def test_chat_toggles_off(fake_update, fake_context):
    from handlers import cmd_chat

    await cmd_chat(fake_update, fake_context)
    await cmd_chat(fake_update, fake_context)

    assert is_direct_chat(fake_context) is False
    reply = fake_update.message.reply_text.await_args.args[0]
    assert "Direct chat off" in reply


async def test_chat_with_text_does_not_mutate_the_message(fake_update, fake_context):
    """The Telegram Message object is immutable — /chat must not write to it.

    Regression test: assigning to update.message.text raises
    AttributeError("Attribute `text` of class `Message` can't be set!"),
    which crashed the handler in production.
    """
    from handlers import cmd_chat

    fake_context.args = ["hello", "there"]

    class ImmutableMessage:
        """Stands in for telegram.Message, which refuses attribute writes."""

        def __init__(self):
            object.__setattr__(self, "text", "original text")
            object.__setattr__(self, "chat", MagicMock(send_action=AsyncMock()))
            object.__setattr__(self, "reply_text", AsyncMock())

        def __setattr__(self, name, value):
            if name == "text" and hasattr(self, "text"):
                raise AssertionError("the handler tried to mutate the Telegram Message")
            object.__setattr__(self, name, value)

    fake_update.message = ImmutableMessage()
    fake_update.message.reply_text = AsyncMock()
    fake_update.message.chat.send_action = AsyncMock()

    with (
        patch("handlers.messages.needs_web"),
        patch("handlers.messages.ask_claude", return_value="Hi"),
    ):
        await cmd_chat(fake_update, fake_context)

    # The original text is untouched and the reply was sent.
    assert fake_update.message.text == "original text"
    fake_update.message.reply_text.assert_awaited_once()


async def test_chat_with_text_answers_directly(fake_update, fake_context):
    """/chat <text> sends the text to the AI without touching the search path."""
    from handlers import cmd_chat

    fake_context.args = ["what", "is", "a", "closure"]

    with (
        patch("handlers.messages.needs_web") as mock_needs,
        patch("handlers.messages.ask_claude", return_value="A closure is...") as mock_ask,
    ):
        await cmd_chat(fake_update, fake_context)

    # The classifier must not be called — that is the whole point.
    mock_needs.assert_not_called()
    mock_ask.assert_called_once()
    assert mock_ask.call_args.args[1] == "what is a closure"


async def test_chat_with_text_does_not_change_the_mode(fake_update, fake_context):
    """/chat <text> answers once but leaves the toggle state alone."""
    from handlers import cmd_chat

    fake_context.args = ["hello"]

    with (
        patch("handlers.messages.needs_web"),
        patch("handlers.messages.ask_claude", return_value="Hi"),
    ):
        await cmd_chat(fake_update, fake_context)

    assert is_direct_chat(fake_context) is False


# ---------------------------------------------------------------------------
# Direct chat mode affects plain messages
# ---------------------------------------------------------------------------
async def test_message_in_direct_mode_skips_classifier(fake_update, fake_context):
    """With the mode on, a plain message never reaches the classifier."""
    from handlers import handle_message

    set_direct_chat(fake_context, True)

    with (
        patch("handlers.messages.needs_web") as mock_needs,
        patch("handlers.messages.ask_claude", return_value="Direct answer") as mock_ask,
    ):
        await handle_message(fake_update, fake_context)

    mock_needs.assert_not_called()
    mock_ask.assert_called_once()


async def test_message_outside_direct_mode_uses_classifier(fake_update, fake_context):
    """Without the mode, the classifier decides as before."""
    from handlers import handle_message

    with (
        patch("handlers.messages.needs_web", return_value=False) as mock_needs,
        patch("handlers.messages.ask_claude", return_value="Answer"),
    ):
        await handle_message(fake_update, fake_context)

    mock_needs.assert_called_once()


async def test_message_outside_direct_mode_still_searches(fake_update, fake_context):
    """Search routing is unchanged when the mode is off."""
    from handlers import handle_message

    with (
        patch("handlers.messages.needs_web", return_value=True),
        patch("handlers.messages.search_web", return_value="Search answer") as mock_search,
        patch("handlers.messages.ask_claude") as mock_ask,
    ):
        await handle_message(fake_update, fake_context)

    mock_search.assert_called_once()
    mock_ask.assert_not_called()


async def test_force_direct_bypasses_the_mode(fake_update, fake_context):
    """force_direct answers directly even when the mode is off."""
    from handlers import handle_message

    with (
        patch("handlers.messages.needs_web") as mock_needs,
        patch("handlers.messages.ask_claude", return_value="Forced"),
    ):
        await handle_message(fake_update, fake_context, force_direct=True)

    mock_needs.assert_not_called()


async def test_search_leaves_direct_mode(fake_update, fake_context):
    """Using /search turns direct chat off — the user wants the search path."""
    from handlers import cmd_search

    set_direct_chat(fake_context, True)
    fake_context.args = ["python", "news"]

    with patch("handlers.commands.search_web", return_value="Results"):
        await cmd_search(fake_update, fake_context)

    assert is_direct_chat(fake_context) is False
