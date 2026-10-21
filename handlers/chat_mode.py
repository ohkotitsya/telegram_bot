"""Direct chat mode — talk to the AI without going through the search pipeline.

Every plain message normally triggers a classifier call (`needs_web`) to
decide whether the question needs live web results. That classifier is a
full extra round-trip to the API on every message, and the search pipeline
that follows is far more expensive again (page fetches plus a summarization
call over a large context).

Direct chat mode skips all of it: the message goes straight to Claude, which
answers from its own knowledge while keeping the conversation history.
"""

from telegram.ext import ContextTypes

# Key under which the mode is stored in the chat's context data.
DIRECT_CHAT_KEY = "direct_chat"


def is_direct_chat(context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Whether this chat currently has direct chat mode enabled."""
    return bool(context.chat_data.get(DIRECT_CHAT_KEY, False))


def set_direct_chat(context: ContextTypes.DEFAULT_TYPE, enabled: bool) -> None:
    """Enable or disable direct chat mode for this chat."""
    context.chat_data[DIRECT_CHAT_KEY] = enabled


def toggle_direct_chat(context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Flip direct chat mode and return the new state."""
    enabled = not is_direct_chat(context)
    set_direct_chat(context, enabled)
    return enabled
