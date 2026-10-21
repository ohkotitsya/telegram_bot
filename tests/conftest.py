"""Shared pytest fixtures."""

import sys
from pathlib import Path

# Make the project importable when pytest is run from anywhere.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Ignore the developer's real .env for the whole test session, so a test run
# can never pick up real credentials or reach the network by accident.
import os  # noqa: E402

os.environ["BOT_SKIP_DOTENV"] = "1"

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch):
    """Keep tests independent of the developer's real environment."""
    for var in (
        "TELEGRAM_BOT_TOKEN",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_BASE_URL",
        "ANTHROPIC_MODEL",
    ):
        monkeypatch.delenv(var, raising=False)
    yield


@pytest.fixture
def reload_config():
    """Return a helper that re-imports the config package with the current env."""

    def _reload():
        import importlib

        for module in list(sys.modules):
            if module == "config" or module.startswith("config."):
                del sys.modules[module]
        return importlib.import_module("config")

    return _reload
