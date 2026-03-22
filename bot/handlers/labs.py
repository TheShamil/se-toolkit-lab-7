"""Handler for the /labs command."""

import httpx


def handle_labs(api_base_url: str, api_key: str) -> str:
    """
    Handle the /labs command by fetching available labs from the backend.

    Args:
        api_base_url: Base URL of the LMS backend API
        api_key: API key for authentication

    Returns:
        List of available labs
    """
    try:
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        response = httpx.get(f"{api_base_url}/items/", headers=headers, timeout=5.0)
        if response.status_code == 200:
            items = response.json()
            if not items:
                return "No labs available"
            # Filter only labs (not tasks) and get their titles
            labs = [item for item in items if item.get("type") == "lab"]
            if not labs:
                return "No labs available"
            lab_names = [item.get("title", "Unknown") for item in labs]
            return "Available labs:\n" + "\n".join(f"• {name}" for name in lab_names)
        return f"⚠️ Backend returned status {response.status_code}"
    except httpx.ConnectError:
        return "❌ Backend is unreachable"
    except httpx.TimeoutException:
        return "❌ Backend request timed out"
