"""Configuration loader for the bot."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env.bot.secret relative to project root (parent of bot/)
BOT_DIR = Path(__file__).parent
PROJECT_ROOT = BOT_DIR.parent
ENV_FILE = PROJECT_ROOT / ".env.bot.secret"


class BotSettings(BaseSettings):
    """Bot configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        populate_by_name=True,
    )

    bot_token: str = Field("", alias="BOT_TOKEN")
    lms_api_base_url: str = Field("http://localhost:42002", alias="LMS_API_BASE_URL")
    lms_api_key: str = Field("", alias="LMS_API_KEY")
    llm_api_key: str = Field("", alias="LLM_API_KEY")
    llm_api_base_url: str = Field("", alias="LLM_API_BASE_URL")
    llm_api_model: str = Field("coder-model", alias="LLM_API_MODEL")


def load_settings() -> BotSettings:
    """Load and return bot settings."""
    return BotSettings()
