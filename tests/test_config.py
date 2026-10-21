"""Tests for the config package."""


def test_config_loads_without_credentials(reload_config):
    """config must import cleanly even with no credentials in the environment."""
    config = reload_config()

    assert config.TELEGRAM_BOT_TOKEN == ""
    assert config.ANTHROPIC_API_KEY == ""
    assert config.AI_AUTH_AVAILABLE is False


def test_default_model_is_set(reload_config):
    config = reload_config()

    assert config.AI_MODEL
    assert isinstance(config.AI_MODEL, str)


def test_history_limit_is_positive(reload_config):
    config = reload_config()

    assert config.MAX_HISTORY > 0
    assert config.AI_MAX_TOKENS > 0


def test_system_prompt_is_non_empty(reload_config):
    config = reload_config()

    assert config.SYSTEM_PROMPT.strip()


def test_auth_available_when_api_key_present(monkeypatch, reload_config):
    """AI_AUTH_AVAILABLE flips to True when a key is in the environment."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    config = reload_config()

    assert config.AI_AUTH_AVAILABLE is True
    assert config.ANTHROPIC_API_KEY == "sk-ant-test-key"


def test_auth_available_with_auth_token_only(monkeypatch, reload_config):
    """The proxy style (ANTHROPIC_AUTH_TOKEN) also enables the AI."""
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "proxy-token")
    config = reload_config()

    assert config.AI_AUTH_AVAILABLE is True


def test_model_can_be_overridden(monkeypatch, reload_config):
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-opus-5-5")
    config = reload_config()

    assert config.AI_MODEL == "claude-opus-5-5"


def test_dotenv_is_skipped_when_flag_set(monkeypatch, reload_config):
    """BOT_SKIP_DOTENV=1 keeps .env out of the environment."""
    monkeypatch.setenv("BOT_SKIP_DOTENV", "1")
    config = reload_config()

    assert config.TELEGRAM_BOT_TOKEN == ""
