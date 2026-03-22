"""Intent router for natural language messages."""

from services.llm_client import LLMClient


def route_intent(
    message: str,
    llm_client: LLMClient,
    api_base_url: str,
    api_key: str,
) -> str:
    """
    Route a natural language message to the appropriate tool(s) via LLM.

    Args:
        message: The user's message
        llm_client: The LLM client instance
        api_base_url: Base URL for the LMS API
        api_key: API key for authentication

    Returns:
        The bot's response
    """
    try:
        return llm_client.chat_with_tools(message, api_base_url, api_key)
    except Exception as e:
        # Handle LLM errors gracefully
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg:
            return "LLM authentication failed. The API token may have expired."
        if "connection" in error_msg.lower() or "timeout" in error_msg.lower():
            return "LLM service is unavailable. Please try again later."
        return f"LLM error: {error_msg}"
