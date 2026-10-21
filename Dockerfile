# syntax=docker/dockerfile:1
#
# Container image for the Telegram AI chatbot.
#
# Anyone who clones the repo can run the bot without installing Python or
# any dependency by hand:
#
#   cp .env.example .env    # fill in your token
#   docker compose up -d
#
# The image contains only the runtime dependencies from requirements.txt and
# the application source. No credentials are baked into the image — secrets
# come from the environment at run time.

# ---------------------------------------------------------------------------
# Stage 1 — build the dependency wheels
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Copied first so the layer is cached until requirements.txt itself changes.
COPY requirements.txt ./

# Build wheels so the final image can install them without a compiler.
RUN pip install --upgrade pip build && \
    pip wheel --wheel-dir /wheels -r requirements.txt


# ---------------------------------------------------------------------------
# Stage 2 — the runtime image
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    BOT_SKIP_DOTENV=1

WORKDIR /app

# Install the pre-built wheels.
COPY --from=builder /wheels /wheels
COPY requirements.txt ./
RUN pip install --no-index --find-links=/wheels -r requirements.txt && \
    rm -rf /wheels

# Application source.
COPY main.py ./
COPY ai/ ./ai/
COPY config/ ./config/
COPY handlers/ ./handlers/

# Run as an unprivileged user.
RUN useradd --create-home --shell /usr/sbin/nologin bot && \
    chown -R bot:bot /app
USER bot

# Fail fast if the bot is misconfigured, instead of crashing on first poll.
HEALTHCHECK --interval=60s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import sys, config; sys.exit(0 if config.TELEGRAM_BOT_TOKEN else 1)"

CMD ["python", "main.py"]
