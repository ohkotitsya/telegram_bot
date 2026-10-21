"""Claude AI client — manages conversation history and API calls."""

import logging

import anthropic

from config import AI_MAX_TOKENS, AI_MODEL, MAX_HISTORY, SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Anthropic client (reads ANTHROPIC_API_KEY from env)
_client = anthropic.Anthropic()

# Per-user conversation history  {chat_id: [messages]}
_conversations: dict[int, list[dict]] = {}

# The provider behind the proxy may attach a memory/skill tool. When the model
# uses it, the tool output arrives as extra "text" blocks whose content is a
# raw marker plus JSON — e.g. "[Skill result: memory_search]{...}". Those
# blocks are not an answer to the user, so they are dropped.
SKILL_MARKER = "[Skill result:"

# How many times to retry when the reply contains nothing but tool output.
MAX_ATTEMPTS = 3


def extract_text(response) -> str:
    """Return the answer text of a response, ignoring tool-output blocks.

    The reply can carry several text blocks: the real answer plus one block
    per tool call the provider made. Only the answer is kept, and the blocks
    are joined in order.
    """
    parts: list[str] = []
    for block in response.content:
        text = getattr(block, "text", None)
        if not isinstance(text, str) or not text.strip():
            continue
        if text.lstrip().startswith(SKILL_MARKER):
            logger.info("Dropping a tool-output block from the reply")
            continue
        parts.append(text)
    return "\n".join(parts).strip()


def ask_claude(chat_id: int, user_message: str) -> str:
    """Send the user message (with history) to Claude and return the reply."""
    history = _conversations.setdefault(chat_id, [])
    history.append({"role": "user", "content": user_message})

    assistant_text = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        # Send a snapshot of the history. The SDK receives its own list, so the
        # appends below cannot mutate a request that is still in flight.
        response = _client.messages.create(
            model=AI_MODEL,
            max_tokens=AI_MAX_TOKENS,
            system=SYSTEM_PROMPT,
            thinking={"type": "adaptive"},
            messages=list(history),
        )

        assistant_text = extract_text(response)
        if assistant_text:
            break

        # The model answered with tool output only. Ask again — the system
        # prompt tells it to skip those tools.
        logger.warning("Reply held no answer text (attempt %d/%d), retrying", attempt, MAX_ATTEMPTS)

    if not assistant_text:
        assistant_text = "🤖 I had no text to return."

    history.append({"role": "assistant", "content": assistant_text})

    # Trim old messages so we don't exceed context limits. This runs after the
    # assistant turn is stored, otherwise the history could end up one message
    # over the cap.
    if len(history) > MAX_HISTORY * 2:
        history[:] = history[-(MAX_HISTORY * 2) :]
    return assistant_text


def clear_history(chat_id: int) -> None:
    """Clear conversation history for a given chat."""
    _conversations.pop(chat_id, None)
