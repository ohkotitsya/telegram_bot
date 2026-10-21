"""Smoke tests for the handlers and the entry point.

These verify wiring — that handlers are registered and that the module
imports — without making any network call.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def fake_update():
    """Build a minimal Update object that looks like Telegram's."""
    update = MagicMock()
    update.effective_chat.id = 12345
    update.message.text = "hello"
    update.message.reply_text = AsyncMock()
    update.message.chat.send_action = AsyncMock()
    return update


@pytest.fixture
def fake_context():
    return MagicMock(args=[])


async def test_cmd_start_replies(fake_update, fake_context):
    from handlers import cmd_start

    await cmd_start(fake_update, fake_context)

    fake_update.message.reply_text.assert_awaited_once()
    reply = fake_update.message.reply_text.await_args.args[0]
    assert "AI-powered chatbot" in reply


async def test_cmd_clear_clears_history(fake_update, fake_context):
    from handlers import cmd_clear

    with patch("handlers.commands.clear_history") as mock_clear:
        await cmd_clear(fake_update, fake_context)

    mock_clear.assert_called_once_with(12345)
    fake_update.message.reply_text.assert_awaited_once()


async def test_cmd_help_lists_commands(fake_update, fake_context):
    from handlers import cmd_help

    await cmd_help(fake_update, fake_context)

    reply = fake_update.message.reply_text.await_args.args[0]
    assert "/start" in reply
    assert "/clear" in reply
    assert "/search" in reply


async def test_cmd_search_requires_query(fake_update, fake_context):
    """Without arguments, /search explains its usage instead of searching."""
    from handlers import cmd_search

    fake_context.args = []
    await cmd_search(fake_update, fake_context)

    reply = fake_update.message.reply_text.await_args.args[0]
    assert "Usage" in reply


async def test_cmd_search_answers_with_sources(fake_update, fake_context):
    from handlers import cmd_search

    fake_context.args = ["python", "news"]

    with patch("handlers.commands.search_web", return_value="Answer. [1]") as mock_search:
        await cmd_search(fake_update, fake_context)

    mock_search.assert_called_once_with("python news")
    assert "Answer" in fake_update.message.reply_text.await_args.args[0]


async def test_handle_message_replies(fake_update, fake_context):
    """A plain message is answered by the AI and replied in chat."""
    from handlers import handle_message

    with (
        patch("handlers.messages.needs_web", return_value=False),
        patch("handlers.messages.ask_claude", return_value="Hi there"),
    ):
        await handle_message(fake_update, fake_context)

    fake_update.message.reply_text.assert_awaited_once()
    assert fake_update.message.reply_text.await_args.args[0] == "Hi there"


async def test_handle_message_splits_long_replies(fake_update, fake_context):
    """Telegram caps messages at 4096 chars — long replies get split."""
    from handlers import handle_message

    long_reply = "x" * 9000

    with (
        patch("handlers.messages.needs_web", return_value=False),
        patch("handlers.messages.ask_claude", return_value=long_reply),
    ):
        await handle_message(fake_update, fake_context)

    assert fake_update.message.reply_text.await_count == 3
    for call in fake_update.message.reply_text.await_args_list:
        assert len(call.args[0]) <= 4096


def test_main_registers_all_handlers():
    """main() wires up every command handler on the Application."""
    from telegram.ext import CommandHandler, MessageHandler

    import main

    captured = {}

    class FakeApp:
        def add_handler(self, handler):
            captured.setdefault("handlers", []).append(handler)

        def run_polling(self, **kwargs):
            captured["polling"] = kwargs

    with (
        patch.object(main, "TELEGRAM_BOT_TOKEN", "test-token"),
        patch.object(main, "AI_AUTH_AVAILABLE", True),
        patch.object(main, "ApplicationBuilder") as builder,
    ):
        builder.return_value.token.return_value.build.return_value = FakeApp()
        main.main()

    handlers = captured["handlers"]
    commands = set()
    for handler in handlers:
        if isinstance(handler, CommandHandler):
            commands |= set(handler.commands)
    assert {"start", "clear", "help", "search"} <= commands
    assert any(isinstance(h, MessageHandler) for h in handlers)
    assert captured["polling"]["drop_pending_updates"] is True


def test_main_exits_without_token():
    """Without a Telegram token, main() exits with a helpful message."""

    import main

    with patch.object(main, "TELEGRAM_BOT_TOKEN", ""), pytest.raises(SystemExit) as exc:
        main.main()

    assert "TELEGRAM_BOT_TOKEN" in str(exc.value)
