"""Handler for the /scores command."""

import httpx


def handle_scores(lab_name: str, api_base_url: str, api_key: str) -> str:
    """
    Handle the /scores command by fetching pass rates for a specific lab.

    Args:
        lab_name: The lab name to get scores for
        api_base_url: Base URL of the LMS backend API
        api_key: API key for authentication

    Returns:
        Pass rates for tasks in the specified lab
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

            # Format the pass rates for each task
            lab_tasks = []
            for item in data:
                task_title = item.get("task_title", "")
                pass_rate = item.get("pass_rate", 0)
                lab_tasks.append(f"• {task_title}: {pass_rate:.1f}% pass rate")

            if not lab_tasks:
                return f"No data found for lab: {lab_name}"

            return f"Scores for '{lab_name}':\n" + "\n".join(lab_tasks)

        return f"⚠️ Backend returned status {response.status_code}"
    except httpx.ConnectError:
        return "❌ Backend is unreachable"
    except httpx.TimeoutException:
        return "❌ Backend request timed out"
