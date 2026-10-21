"""
Telegram Bot with AI Chat — powered by Claude (Anthropic).

Entry point. Run with:  python main.py
"""

import logging
import sys

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import AI_AUTH_AVAILABLE, TELEGRAM_BOT_TOKEN
from handlers import cmd_chat, cmd_clear, cmd_help, cmd_search, cmd_start, handle_message

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        sys.exit("TELEGRAM_BOT_TOKEN is not set. Copy .env.example to .env and fill in your token.")

    if not AI_AUTH_AVAILABLE:
        sys.exit(
            "No AI credentials found. Set either ANTHROPIC_API_KEY or "
            "ANTHROPIC_AUTH_TOKEN (the environment already provides "
            "ANTHROPIC_AUTH_TOKEN if this is the same machine as your AI proxy)."
        )

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(CommandHandler("chat", cmd_chat))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("search", cmd_search))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🤖 Bot is starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
