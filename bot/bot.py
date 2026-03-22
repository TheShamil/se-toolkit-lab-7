"""
LMS Telegram Bot entry point.

Supports two modes:
- Telegram mode (default): Connects to Telegram and handles real messages
- Test mode (--test): Prints responses to stdout for offline testing
"""

import argparse
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from config import load_settings
from handlers.start import handle_start
from handlers.help import handle_help
from handlers.health import handle_health
from handlers.labs import handle_labs
from handlers.scores import handle_scores


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def handle_command(command: str, settings) -> str:
    """
    Route a command to the appropriate handler and return the response.

    Args:
        command: The command string, e.g. "/start" or "/help"
        settings: Loaded bot settings

    Returns:
        The handler's text response
    """
    # Strip leading slash and split into command and arguments
    parts = command.lstrip("/").split()
    cmd = parts[0]
    args = parts[1:] if len(parts) > 1 else []

    if cmd == "start":
        return handle_start()

    if cmd == "help":
        return handle_help()

    if cmd == "health":
        return handle_health(settings.lms_api_base_url)

    if cmd == "labs":
        return handle_labs(settings.lms_api_base_url, settings.lms_api_key)

    if cmd == "scores":
        if not args:
            return "Usage: /scores <lab-name>"
        lab_name = " ".join(args)
        return handle_scores(lab_name, settings.lms_api_base_url, settings.lms_api_key)

    return "Command not implemented yet"


async def telegram_mode(settings) -> None:
    """Run the bot in Telegram mode."""
    if not settings.bot_token:
        logger.error("BOT_TOKEN not set. Please configure .env.bot.secret")
        sys.exit(1)

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def start_handler(message: Message) -> None:
        """Handle /start command."""
        response = handle_start()
        await message.answer(response)

    @dp.message(Command("help"))
    async def help_handler(message: Message) -> None:
        """Handle /help command."""
        response = handle_help()
        await message.answer(response)

    @dp.message(Command("health"))
    async def health_handler(message: Message) -> None:
        """Handle /health command."""
        response = handle_health(settings.lms_api_base_url)
        await message.answer(response)

    @dp.message(Command("labs"))
    async def labs_handler(message: Message) -> None:
        """Handle /labs command."""
        response = handle_labs(settings.lms_api_base_url, settings.lms_api_key)
        await message.answer(response)

    @dp.message(Command("scores"))
    async def scores_handler(message: Message) -> None:
        """Handle /scores command."""
        # Extract lab name from command arguments
        lab_name = message.text.split(maxsplit=1)[1] if " " in message.text else ""
        if not lab_name:
            response = "Usage: /scores <lab-name>"
        else:
            response = handle_scores(lab_name, settings.lms_api_base_url, settings.lms_api_key)
        await message.answer(response)

    logger.info("Bot is starting in Telegram mode...")
    await dp.start_polling(bot)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="LMS Telegram Bot")
    parser.add_argument(
        "--test",
        type=str,
        metavar="COMMAND",
        help="Test mode: print response to stdout instead of connecting to Telegram",
    )

    args = parser.parse_args()

    # Load settings from .env.bot.secret
    settings = load_settings()

    if args.test:
        # Test mode: call handler directly and print result
        response = handle_command(args.test, settings)
        print(response)
        sys.exit(0)

    # Telegram mode
    asyncio.run(telegram_mode(settings))


if __name__ == "__main__":
    main()
