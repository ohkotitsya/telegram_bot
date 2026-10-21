"""Command handlers — /start, /clear, /help, /search."""

import anthropic
from telegram import Update
from telegram.ext import ContextTypes

from ai.client import clear_history
from ai.search import search_web


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — greet the user."""
    await update.message.reply_text(
        "👋 Hi! I'm an AI-powered chatbot using Claude.\n\n"
        "Just send me any message and I'll reply!\n\n"
        "Commands:\n"
        "/start  — show this message\n"
        "/clear  — clear conversation history\n"
        "/search — search the web like Google\n"
        "/help   — show help"
    )


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /clear — reset conversation history."""
    chat_id = update.effective_chat.id
    clear_history(chat_id)
    await update.message.reply_text("🗑️ Conversation history cleared!")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help."""
    await update.message.reply_text(
        "🤖 *AI Chatbot Help*\n\n"
        "Send me any text message and I'll reply using AI.\n\n"
        "I remember the conversation context so you can have "
        "a natural back-and-forth chat.\n\n"
        "*Commands:*\n"
        "/start — welcome message\n"
        "/clear — forget our conversation\n"
        "/search \\[query\\] — search the web like Google\n"
        "/help  — this message",
        parse_mode="Markdown",
    )


async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /search <query> — search the web and answer with sources."""
    if not context.args:
        await update.message.reply_text(
            "🔍 Usage: /search <what to look for>\n\nExample: /search latest python news"
        )
        return

    query = " ".join(context.args)

    # Show "typing…" while we wait for the AI + web search
    await update.message.chat.send_action("typing")

    try:
        answer = search_web(query)
    except anthropic.RateLimitError:
        answer = "⏳ I'm getting too many requests right now. Please try again in a moment."
    except anthropic.APIStatusError:
        answer = "❌ Sorry, something went wrong with the AI service."
    except anthropic.APIConnectionError:
        answer = "🌐 I can't reach the AI service right now. Please try again later."

    # Telegram messages have a 4096-char limit — split if needed
    for i in range(0, len(answer), 4096):
        await update.message.reply_text(answer[i : i + 4096], parse_mode="Markdown")
