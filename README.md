# 🤖 Telegram AI Chatbot

A Telegram chatbot powered by **Claude AI** (Anthropic). Send any message and get intelligent AI responses with conversation memory.

## Changelog

### v1.1.0

- 💬 **`/chat`** — talk directly to the AI. Messages skip the "does this need
  a web search?" classifier and the whole search pipeline, so replies are
  faster and use fewer tokens. The mode is per chat; send `/chat` again to
  switch back. Using `/search` turns it off.

### v1.0.0

- 🤖 Telegram bot with Claude, conversation memory and per-user history
- 🔍 Web search (DuckDuckGo + Wikipedia) with AI summarization and sources
- 🐳 Docker image and GitHub Actions CI
- 🧪 47-test suite, running fully offline

## Features

- 💬 Natural conversation with Claude AI (Sonnet 5.5)
- 🧠 Remembers conversation context per user
- 🌍 Replies in the same language you write
- 🔍 Searches the web when a question needs current information
- 💬 `/chat` talks straight to the AI — no search, fewer tokens
- 🗑️ Clear history with `/clear`
- ⚡ Handles errors and rate limits gracefully
- 🐳 Ships with a Docker image and CI — clone and run, no manual setup

## Quick start (Docker — recommended)

Everything you need is in the repo. No manual Python or dependency setup:

```bash
git clone https://github.com/ohkotitsya/telegram_bot.git
cd telegram_bot

cp .env.example .env      # then edit .env and paste your keys
docker compose up -d      # builds the image and starts the bot
docker compose logs -f    # watch the logs
```

Stop it with `docker compose down`.

## Quick start (local Python)

Requires Python 3.11 or newer.

```bash
git clone https://github.com/ohkotitsya/telegram_bot.git
cd telegram_bot

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env             # then edit .env and paste your keys
python main.py
```

Or install the project itself, which pulls in every dependency:

```bash
pip install -e ".[dev]"
```

## Getting your keys

- **Telegram Bot Token**: talk to [@BotFather](https://t.me/BotFather) on
  Telegram, send `/newbot`, and follow the steps.
- **Anthropic API Key**: sign up at
  [console.anthropic.com](https://console.anthropic.com/) and create a key.
- **Third-Part API Host**: required `ANTHROPIC_AUTH_TOKEN` + `ANTHROPIC_BASE_URL`

Put them in `.env`:

```
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
ANTHROPIC_API_KEY=sk-ant-api03-...
```

`.env` is gitignored — it never leaves your machine and is never committed.

## Project Structure

```
telegram_bot/
├── main.py                  # Entry point — starts the bot
├── config/
│   └── __init__.py          # Settings, env vars, AI model config
├── ai/
│   ├── __init__.py          # Exports ask_claude
│   ├── client.py            # Claude API calls + conversation history
│   └── search.py            # Web search (DuckDuckGo + Wikipedia) + AI summary
├── handlers/
│   ├── __init__.py          # Exports all handlers
│   ├── commands.py          # /start, /clear, /help, /search commands
│   └── messages.py          # Text message → AI → reply
├── tests/                   # Test suite (pytest, no network needed)
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_ai_client.py
│   ├── test_search.py
│   └── test_handlers.py
├── .github/workflows/
│   └── python-package.yml   # CI: lint, test, Docker build
├── Dockerfile                # Container image (multi-stage)
├── docker-compose.yml       # One-command run
├── .dockerignore
├── pyproject.toml            # Package metadata, ruff & pytest config
├── requirements.txt         # Python dependencies
├── .env.example             # Template for environment variables (committed)
├── .env                     # Your actual keys (never committed)
├── .gitignore               # Ignores .env and cache files
├── .gitattributes           # Normalizes line endings (LF) for the deploy host
├── LICENSE
└── README.md                # This file
```

### How the modules connect

```
main.py
 ├── config/          → loads .env, exposes settings (token, API key, model, prompt)
 ├── handlers/
 │   ├── commands.py  → uses ai.client.clear_history()
 │   └── messages.py  → uses ai.ask_claude()
 └── ai/
     ├── client.py    → uses config settings, calls Anthropic API
     └── search.py    → DuckDuckGo + Wikipedia, then AI summarizes
```

## Development

```bash
pip install -e ".[dev]"

ruff check .          # lint
ruff format .         # format
pytest                # run the tests
```

The test suite mocks the Anthropic API and all network calls, so it runs
offline and never touches your real credentials.

## Bot Commands

| Command  | Description                  |
|----------|------------------------------|
| `/start` | Welcome message              |
| `/clear` | Clear conversation history   |
| `/chat` | Talk directly to the AI, skipping web search |
| `/search` | Search the web and answer with sources |
| `/help`  | Show help                    |

### Direct chat (`/chat`)

By default every message goes through a router: the bot asks the AI whether
the question needs live web results, and only then decides between answering
from its own knowledge or running the full search pipeline.

`/chat` turns that routing off. Your messages go straight to Claude, which
means:

- **No classifier call** — one less round-trip to the API per message
- **No web search** — no DuckDuckGo/Wikipedia calls, no page fetching
- **Faster and cheaper** — especially for long conversations, where the
  search path would otherwise pull a large context into every request

Send `/chat` again to switch back. The mode is per chat, so it doesn't affect
other users of the same bot.

```
/chat                     → toggles direct chat on/off
/chat what's a closure?   → answers that message directly, mode unchanged
```

Using `/search` turns direct chat off, since asking for a search means you
want the search path.

## Deploy

The bot reads its secrets from the environment at runtime, so `.env` is never
needed on the server — and is never committed.

### Option A — Docker (any host)

```bash
docker build -t telegram-bot .
docker run -d --name telegram-bot \
  --env-file .env \
  --restart unless-stopped \
  telegram-bot
```

The image is a multi-stage build: wheels are compiled in the builder stage and
only the runtime dependencies and source land in the final image, which runs
as an unprivileged user.

### Option B — Platform as a Service

Point the platform at the repo and it will use `requirements.txt` and the
`main.py` entry point. Set the secrets below in the platform's dashboard.

For Render or Railway, the start command is:

```
python main.py
```

### Secrets on the host

Set these as real environment variables in your platform's dashboard (Render,
Railway, Heroku, systemd `EnvironmentFile`, Docker `--env-file`, etc.):

- `TELEGRAM_BOT_TOKEN` — required, from @BotFather
- `ANTHROPIC_API_KEY` — required, or `ANTHROPIC_AUTH_TOKEN` + `ANTHROPIC_BASE_URL`
- `ANTHROPIC_MODEL` — optional, overrides the default model

Never commit real values of these to `.env.example`.

The container sets `BOT_SKIP_DOTENV=1`, so it reads only the injected
environment variables and ignores any `.env` file. On a bare host, `.env` in
the project root is loaded automatically.

### Files that MUST be committed

If the deploy fails with "module not found" or "requirements.txt missing",
a file was excluded by `.gitignore`. These must all be tracked:

| File | Why |
|------|-----|
| `main.py` | Entry point |
| `requirements.txt` | `pip install -r requirements.txt` during build |
| `pyproject.toml` | Package metadata and tool configuration |
| `.env.example` | Template documenting which variables to set (no real secrets) |
| `ai/`, `config/`, `handlers/` | Application source |
| `Dockerfile`, `docker-compose.yml` | Container build and orchestration |
| `.github/workflows/python-package.yml` | CI — lint, test, image build |

Verify before deploying:

```bash
git ls-files | grep -E 'main.py|requirements.txt|\.env\.example|Dockerfile'
```

### Line endings

`.gitattributes` forces LF on checkout, so the Linux deploy host gets
correctly formatted files regardless of your local Windows `core.autocrlf`.

### Continuous integration

`.github/workflows/python-package.yml` runs on every push and pull request:

- **Lint & format** — `ruff check` and `ruff format --check`
- **Tests** — the pytest suite on Python 3.11, 3.12 and 3.13
- **Docker build** — verifies the image still builds

## License

MIT — see [LICENSE](LICENSE).
