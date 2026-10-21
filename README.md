# 🤖 Telegram AI Chatbot

A Telegram chatbot powered by **Claude AI** (Anthropic). Send any message and get intelligent AI responses with conversation memory.

## Features

- 💬 Natural conversation with Claude AI (Sonnet 5.5)
- 🧠 Remembers conversation context per user
- 🌍 Replies in the same language you write
- 🗑️ Clear history with `/clear`
- ⚡ Handles errors and rate limits gracefully

## Project Structure

```
chatbot/
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
├── requirements.txt         # Python dependencies
├── .env.example             # Template for environment variables (committed)
├── .env                     # Your actual keys (never committed)
├── .gitignore               # Ignores .env and cache files
├── .gitattributes           # Normalizes line endings (LF) for the deploy host
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
     └── client.py    → uses config settings, calls Anthropic API
```

## Setup

### 1. Get your API keys

- **Telegram Bot Token**: Talk to [@BotFather](https://t.me/BotFather) on Telegram, send `/newbot`, and follow the steps. Copy the token.
- **Anthropic API Key**: Sign up at [console.anthropic.com](https://console.anthropic.com/) and create an API key.

### 2. Install dependencies

```bash
cd chatbot
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in your keys:

```
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
ANTHROPIC_API_KEY=sk-ant-api03-...
```

### 4. Run the bot

```bash
python main.py
```

## Bot Commands

| Command  | Description                  |
|----------|------------------------------|
| `/start` | Welcome message              |
| `/clear` | Clear conversation history   |
| `/search` | Search the web and answer with sources |
| `/help`  | Show help                    |

## Deploy

The bot reads its secrets from the environment at runtime, so `.env` is never
needed on the server — and is never committed.

### Files that MUST be committed

If the deploy fails with "module not found" or "requirements.txt missing",
a file was excluded by `.gitignore`. These must all be tracked:

| File | Why |
|------|-----|
| `main.py` | Entry point |
| `requirements.txt` | `pip install -r requirements.txt` during build |
| `.env.example` | Template documenting which variables to set (no real secrets) |
| `ai/`, `config/`, `handlers/` | Application source |
| `requirements.txt`, `Procfile`, `Dockerfile`, `render.yaml`, `railway.json` | Platform config, if you use one |

Verify before deploying:

```bash
git ls-files | grep -E 'main.py|requirements.txt|\.env\.example'
```

### Secrets on the host

Set these as real environment variables in your platform's dashboard (Render,
Railway, Heroku, systemd `EnvironmentFile`, Docker `--env-file`, etc.):

- `TELEGRAM_BOT_TOKEN` — required, from @BotFather
- `ANTHROPIC_API_KEY` — required, or `ANTHROPIC_AUTH_TOKEN` + `ANTHROPIC_BASE_URL`
- `ANTHROPIC_MODEL` — optional, overrides the default model

Never commit real values of these to `.env.example`.

### Line endings

`.gitattributes` forces LF on checkout, so the Linux deploy host gets
correctly formatted files regardless of your local Windows `core.autocrlf`.
