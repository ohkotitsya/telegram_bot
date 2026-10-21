"""Config package — loads environment variables and app settings."""

import os

from dotenv import load_dotenv

# Load .env from the project root. Set BOT_SKIP_DOTENV=1 to ignore it — useful
# in tests (so a developer's real credentials never leak into a test run) and
# on hosts where secrets are injected as real environment variables.
if not os.getenv("BOT_SKIP_DOTENV"):
    load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Anthropic auth — the SDK picks up ANTHROPIC_AUTH_TOKEN / ANTHROPIC_BASE_URL
# from the environment automatically (the same provider this machine already
# uses), but a classic ANTHROPIC_API_KEY also works.
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
AI_AUTH_AVAILABLE = bool(ANTHROPIC_API_KEY or os.getenv("ANTHROPIC_AUTH_TOKEN"))

# AI settings — use the model from the environment when provided.
# Note: when a proxy (ANTHROPIC_BASE_URL) is in use, its own ANTHROPIC_MODEL
# may override this. A proxy may also reject models it has no key for, which
# surfaces as HTTP 402 "premium_model_requires_key".
AI_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
AI_MAX_TOKENS = 4096
MAX_HISTORY = 20  # max message pairs to keep per user

SYSTEM_PROMPT = (
    "You are a friendly and helpful AI assistant on Telegram. "
    "Answer concisely but thoroughly. Use emojis where appropriate. "
    "If the user writes in a language other than English, reply in that same language. "
    # The provider behind the proxy may expose a memory/skill tool. Its output
    # is injected as extra "text" blocks in the reply, which would leak raw
    # JSON into the chat. The model is told to answer without those tools.
    "Do not use any memory, search, or skill tools. Never mention memory. "
    "Just answer the user directly."
)
