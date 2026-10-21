"""Config package — loads environment variables and app settings."""

import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Anthropic auth — the SDK picks up ANTHROPIC_AUTH_TOKEN / ANTHROPIC_BASE_URL
# from the environment automatically (the same provider this machine already
# uses), but a classic ANTHROPIC_API_KEY also works.
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
AI_AUTH_AVAILABLE = bool(ANTHROPIC_API_KEY or os.getenv("ANTHROPIC_AUTH_TOKEN"))

# AI settings — use the model from the environment when provided
AI_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
AI_MAX_TOKENS = 4096
MAX_HISTORY = 20  # max message pairs to keep per user

SYSTEM_PROMPT = (
    "You are a friendly and helpful AI assistant on Telegram. "
    "Answer concisely but thoroughly. Use emojis where appropriate. "
    "If the user writes in a language other than English, reply in that same language."
)
