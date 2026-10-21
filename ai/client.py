"""Claude AI client — manages conversation history and API calls."""

import anthropic

from config import AI_MAX_TOKENS, AI_MODEL, MAX_HISTORY, SYSTEM_PROMPT

# Anthropic client (reads ANTHROPIC_API_KEY from env)
_client = anthropic.Anthropic()

# Per-user conversation history  {chat_id: [messages]}
_conversations: dict[int, list[dict]] = {}


def ask_claude(chat_id: int, user_message: str) -> str:
    """Send the user message (with history) to Claude and return the reply."""
    history = _conversations.setdefault(chat_id, [])
    history.append({"role": "user", "content": user_message})

    # Send a snapshot of the history. The SDK receives its own list, so the
    # appends below cannot mutate a request that is still in flight.
    response = _client.messages.create(
        model=AI_MODEL,
        max_tokens=AI_MAX_TOKENS,
        system=SYSTEM_PROMPT,
        thinking={"type": "adaptive"},
        messages=list(history),
    )

    # Extract the text reply
    assistant_text = next(
        (block.text for block in response.content if block.type == "text"),
        "🤖 I had no text to return.",
    )

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
