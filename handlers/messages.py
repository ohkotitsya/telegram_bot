"""Message handler — answers user text, auto-searching the web when needed."""

import logging

import anthropic
from telegram import Update
from telegram.ext import ContextTypes

from ai import ask_claude, search_web
from ai.search import needs_web

logger = logging.getLogger(__name__)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle any text message.

    The bot first decides whether the question needs live web results
    (news, prices, weather, scores...). If yes, it runs the full search
    engine and answers with sources. Otherwise, it replies from the AI's
    own knowledge with conversation memory.
    """
    chat_id = update.effective_chat.id
    user_text = update.message.text

    logger.info("Message from %s: %s", chat_id, user_text[:80])

    # Show "typing…" while we wait for the AI
    await update.message.chat.send_action("typing")

    try:
        if needs_web(user_text):
            # Time-sensitive question — run the search engine
            logger.info("Routing to web search: %s", user_text[:60])
            reply = search_web(user_text)
        else:
            # Normal chat — answer with conversation memory
            reply = ask_claude(chat_id, user_text)
    except anthropic.RateLimitError:
        reply = "⏳ I'm getting too many requests right now. Please try again in a moment."
    except anthropic.APIStatusError as exc:
        logger.error("Anthropic API error: %s", exc)
        reply = "❌ Sorry, something went wrong with the AI service."
    except anthropic.APIConnectionError:
        reply = "🌐 I can't reach the AI service right now. Please try again later."

    # Telegram messages have a 4096-char limit — split if needed
    for i in range(0, len(reply), 4096):
        await update.message.reply_text(reply[i : i + 4096])
