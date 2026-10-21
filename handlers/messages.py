"""Message handler — answers user text, auto-searching the web when needed."""

import logging

import anthropic
from telegram import Update
from telegram.ext import ContextTypes

from ai import ask_claude, search_web
from ai.search import needs_web
from handlers.chat_mode import is_direct_chat

logger = logging.getLogger(__name__)


def build_reply(
    chat_id: int,
    user_text: str,
    context: ContextTypes.DEFAULT_TYPE,
    force_direct: bool = False,
) -> str:
    """Produce the reply for a user message.

    By default the bot first decides whether the question needs live web
    results (news, prices, weather, scores...). If yes, it runs the full
    search engine and answers with sources. Otherwise, it replies from the
    AI's own knowledge with conversation memory.

    When direct chat mode is on (see /chat), or when ``force_direct`` is
    set, the message goes straight to the AI. That skips the classifier call
    and the search pipeline, which saves tokens and reduces latency.
    """
    logger.info("Message from %s: %s", chat_id, user_text[:80])

    direct = force_direct or is_direct_chat(context)

    try:
        if not direct and needs_web(user_text):
            # Time-sensitive question — run the search engine
            logger.info("Routing to web search: %s", user_text[:60])
            return search_web(user_text)

        # Normal chat — answer with conversation memory
        if direct:
            logger.info("Direct chat: %s", user_text[:60])
        return ask_claude(chat_id, user_text)
    except anthropic.RateLimitError:
        return "⏳ I'm getting too many requests right now. Please try again in a moment."
    except anthropic.APIStatusError as exc:
        logger.error("Anthropic API error: %s", exc)
        # 402 means the provider rejected the request for billing/key reasons
        # (a proxy that has no key for the requested model, for instance).
        # A generic "something went wrong" hides the real cause, so spell it
        # out for the operator.
        if exc.status_code == 402:
            return (
                "❌ The AI provider rejected the request (HTTP 402).\n\n"
                "This usually means the configured model needs a provider key "
                "that isn't set. Check ANTHROPIC_API_KEY / ANTHROPIC_BASE_URL."
            )
        return "❌ Sorry, something went wrong with the AI service."
    except anthropic.APIConnectionError:
        return "🌐 I can't reach the AI service right now. Please try again later."


async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    force_direct: bool = False,
) -> None:
    """Handle any text message and send the reply."""
    chat_id = update.effective_chat.id
    user_text = update.message.text

    # Show "typing…" while we wait for the AI
    await update.message.chat.send_action("typing")

    reply = build_reply(chat_id, user_text, context, force_direct=force_direct)

    # Telegram messages have a 4096-char limit — split if needed
    for i in range(0, len(reply), 4096):
        await update.message.reply_text(reply[i : i + 4096])
