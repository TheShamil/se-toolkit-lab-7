"""Handler for the /scores command."""

import httpx


def handle_scores(lab_name: str, api_base_url: str, api_key: str) -> str:
    """
    Handle the /scores command by fetching scores for a specific lab.

    Args:
        lab_name: The lab name to get scores for
        api_base_url: Base URL of the LMS backend API
        api_key: API key for authentication

    Returns:
        Average scores for tasks in the specified lab
    """
    try:
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        response = httpx.get(
            f"{api_base_url}/analytics/pass-rates",
            params={"lab": lab_name},
            headers=headers,
            timeout=5.0,
        )
        if response.status_code == 200:
            data = response.json()
            if not data:
                return f"No data found for lab: {lab_name}"

            # Format the scores for each task
            lab_tasks = []
            for item in data:
                task_title = item.get("task", "")
                avg_score = item.get("avg_score", 0)
                attempts = item.get("attempts", 0)
                lab_tasks.append(f"• {task_title}: {avg_score:.1f}% avg score ({attempts} attempts)")

            if not lab_tasks:
                return f"No data found for lab: {lab_name}"

            return f"Scores for '{lab_name}':\n" + "\n".join(lab_tasks)

        return f"⚠️ Backend returned status {response.status_code}"
    except httpx.ConnectError as e:
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
