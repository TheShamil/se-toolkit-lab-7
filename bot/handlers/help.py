"""Handler for the /help command."""


def handle_help() -> str:
    """
    Handle the /help command.

    Returns:
        List of available commands with descriptions
    """
    return """Available commands:
/start — Welcome message
/help — Show this help message
/health — Check backend system status
/labs — List available labs
/scores <lab> — Show pass rates for a specific lab"""
