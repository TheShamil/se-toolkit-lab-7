"""Handler for the /health command."""

import httpx


def handle_health(api_base_url: str, api_key: str = "") -> str:
    """
    Handle the /health command by checking backend status.

    Args:
        api_base_url: Base URL of the LMS backend API
        api_key: API key for authentication (optional)

    Returns:
        Health status message
    """
    try:
        # Check the health endpoint first
        response = httpx.get(f"{api_base_url}/health", timeout=5.0)
        if response.status_code == 200:
            # Also check if we can fetch items to prove data is available
            try:
                headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
                items_response = httpx.get(f"{api_base_url}/items/", headers=headers, timeout=5.0)
                if items_response.status_code == 200:
                    items = items_response.json()
                    return f"✅ Backend is healthy. {len(items)} items available."
            except Exception:
                pass  # Health is OK but data fetch failed - still report healthy
            return "✅ Backend is healthy"
        return f"⚠️ Backend returned status {response.status_code}"
    except httpx.ConnectError as e:
        # Extract the error reason from the exception
        error_msg = str(e)
        if "Connection refused" in error_msg:
            return f"❌ Backend error: connection refused ({api_base_url}). Check that the services are running."
        return f"❌ Backend error: {error_msg}"
    except httpx.TimeoutException:
        return "❌ Backend request timed out"
    except httpx.HTTPStatusError as e:
        return f"❌ Backend error: HTTP {e.response.status_code} {e.response.reason_phrase}. The backend service may be down."
    except Exception as e:
        return f"❌ Backend error: {str(e)}"
