"""Handler for the /health command."""

import httpx


def handle_health(api_base_url: str) -> str:
    """
    Handle the /health command by checking backend status.

    Args:
        api_base_url: Base URL of the LMS backend API

    Returns:
        Health status message
    """
    try:
        response = httpx.get(f"{api_base_url}/health", timeout=5.0)
        if response.status_code == 200:
            return "✅ Backend is healthy"
        return f"⚠️ Backend returned status {response.status_code}"
    except httpx.ConnectError:
        return "❌ Backend is unreachable"
    except httpx.TimeoutException:
        return "❌ Backend request timed out"
