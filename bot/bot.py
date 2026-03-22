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
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import load_settings
from handlers.start import handle_start
from handlers.help import handle_help
from handlers.health import handle_health
from handlers.labs import handle_labs
from handlers.scores import handle_scores
from handlers.intent_router import route_intent
from services.llm_client import LLMClient


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_helpful_response(message: str, settings) -> str:
    """
    Get a helpful response for non-command messages using LLM.

    Args:
        message: The user's message
        settings: Loaded bot settings

    Returns:
        The bot's response
    """
    llm_client = LLMClient(
        api_base_url=settings.llm_api_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_api_model,
    )
    return route_intent(
        message,
        llm_client,
        settings.lms_api_base_url,
        settings.lms_api_key,
    )


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
        return handle_health(settings.lms_api_base_url, settings.lms_api_key)

    if cmd == "labs":
        return handle_labs(settings.lms_api_base_url, settings.lms_api_key)

    if cmd == "scores":
        if not args:
            return "Usage: /scores <lab-name>"
        lab_name = " ".join(args)
        return handle_scores(lab_name, settings.lms_api_base_url, settings.lms_api_key)

    # Unknown command - use LLM to provide helpful response
    return get_helpful_response(command, settings)


def create_main_keyboard() -> InlineKeyboardMarkup:
    """Create inline keyboard with common actions."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Health", callback_data="health"),
            InlineKeyboardButton(text="📚 Labs", callback_data="labs"),
        ],
        [
            InlineKeyboardButton(text="📈 Scores", callback_data="scores lab-04"),
            InlineKeyboardButton(text="❓ Help", callback_data="help"),
        ],
    ])
    return keyboard


async def telegram_mode(settings) -> None:
    """Run the bot in Telegram mode."""
    if not settings.bot_token:
        logger.error("BOT_TOKEN not set. Please configure .env.bot.secret")
        sys.exit(1)

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    # Initialize LLM client
    llm_client = LLMClient(
        api_base_url=settings.llm_api_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_api_model,
    )

    @dp.message(CommandStart())
    async def start_handler(message: Message) -> None:
        """Handle /start command."""
        response = handle_start()
        await message.answer(response, reply_markup=create_main_keyboard())

    @dp.message(Command("help"))
    async def help_handler(message: Message) -> None:
        """Handle /help command."""
        response = handle_help()
        await message.answer(response)

    @dp.message(Command("health"))
    async def health_handler(message: Message) -> None:
        """Handle /health command."""
        response = handle_health(settings.lms_api_base_url, settings.lms_api_key)
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

    @dp.message()
    async def handle_natural_language(message: Message) -> None:
        """Handle natural language messages using LLM intent routing."""
        user_message = message.text or ""

        # Log the message for debugging
        logger.info(f"Received message: {user_message}")

        try:
            response = route_intent(
                user_message,
                llm_client,
                settings.lms_api_base_url,
                settings.lms_api_key,
            )
            await message.answer(response)
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await message.answer(
                "Sorry, I encountered an error processing your request. Please try again."
            )

    @dp.callback_query()
    async def handle_callback(callback: types.CallbackQuery) -> None:
        """Handle inline keyboard button callbacks."""
        action = callback.data

        if action == "health":
            response = handle_health(settings.lms_api_base_url, settings.lms_api_key)
        elif action == "labs":
            response = handle_labs(settings.lms_api_base_url, settings.lms_api_key)
        elif action == "help":
            response = handle_help()
        elif action.startswith("scores"):
            lab_name = action.split(maxsplit=1)[1] if " " in action else "lab-04"
            response = handle_scores(lab_name, settings.lms_api_base_url, settings.lms_api_key)
        else:
            response = "Unknown action"

        await callback.message.answer(response)
        await callback.answer()

    logger.info("Bot is starting in Telegram mode...")
    await dp.start_polling(bot)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="LMS Telegram Bot")
    parser.add_argument(
        "--test",
        type=str,
        metavar="MESSAGE",
        help="Test mode: print response to stdout instead of connecting to Telegram",
    )

    args = parser.parse_args()

    # Load settings from .env.bot.secret
    settings = load_settings()

    if args.test:
        # Test mode: handle command or natural language message
        user_input = args.test

        # Check if it's a slash command
        if user_input.startswith("/"):
            response = handle_command(user_input, settings)
        else:
            # Natural language - use LLM intent routing
            response = get_helpful_response(user_input, settings)

        print(response)
        sys.exit(0)

    # Telegram mode
    asyncio.run(telegram_mode(settings))


if __name__ == "__main__":
    main()
