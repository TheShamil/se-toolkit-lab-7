"""LLM client with tool calling support."""

import json
import logging
import sys
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Define the 9 backend endpoints as LLM tools
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_items",
            "description": "Get list of all labs and tasks. Use this when user asks about available labs, what exists, or wants to browse.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_learners",
            "description": "Get list of enrolled learners and their groups. Use when user asks about students, enrollment, or who is taking the course.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_scores",
            "description": "Get score distribution (4 buckets: 0-25, 26-50, 51-75, 76-100) for a specific lab. Use when user asks about score distribution or how students performed in ranges.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier, e.g. 'lab-01', 'lab-04'. Must be in format 'lab-XX'.",
                    }
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pass_rates",
            "description": "Get per-task average scores and attempt counts for a specific lab. Use when user asks about task difficulty, pass rates, or how students did on specific tasks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier, e.g. 'lab-01', 'lab-04'. Must be in format 'lab-XX'.",
                    }
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_timeline",
            "description": "Get submission timeline showing submissions per day for a lab. Use when user asks about when students submitted, activity over time, or submission patterns.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier, e.g. 'lab-01', 'lab-04'.",
                    }
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_groups",
            "description": "Get per-group performance for a lab, including average scores and student counts. Use when user asks about which group is best, group comparison, or group performance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier, e.g. 'lab-01', 'lab-04'.",
                    }
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_learners",
            "description": "Get top N learners by score for a lab. Use when user asks about best students, leaderboard, top performers, or who did best.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier, e.g. 'lab-01', 'lab-04'.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of top learners to return, default 5.",
                        "default": 5,
                    },
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_completion_rate",
            "description": "Get completion rate percentage for a lab. Use when user asks about how many students finished, completion percentage, or what fraction completed the lab.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier, e.g. 'lab-01', 'lab-04'.",
                    }
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_sync",
            "description": "Trigger ETL sync to refresh data from the autochecker. Use when user asks to update data, refresh stats, or sync results.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]

SYSTEM_PROMPT = """You are a helpful assistant for a Learning Management System. You have access to tools that let you query data about labs, students, scores, and analytics.

When a user asks a question:
1. First, decide which tool(s) to call to get the data you need
2. Call the tools with the correct parameters
3. Once you have the data, summarize it clearly for the user

If the user asks something that doesn't require data (like a greeting), respond naturally without calling tools.

If you don't understand the user's question, ask for clarification or explain what you can help with.

Available tools:
- get_items: List all labs and tasks
- get_learners: List enrolled students
- get_scores: Score distribution for a lab
- get_pass_rates: Per-task scores for a lab
- get_timeline: Submission timeline for a lab
- get_groups: Per-group performance for a lab
- get_top_learners: Top students for a lab
- get_completion_rate: Completion percentage for a lab
- trigger_sync: Refresh data from autochecker
"""


class LLMClient:
    """Client for interacting with the LLM API with tool calling support."""

    def __init__(
        self,
        api_base_url: str,
        api_key: str,
        model: str = "coder-model",
    ):
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.client = httpx.Client(timeout=30.0)

    def _debug(self, message: str) -> None:
        """Print debug message to stderr."""
        print(message, file=sys.stderr)

    def chat_with_tools(
        self, user_message: str, api_base_url: str, api_key: str
    ) -> str:
        """
        Send a message to the LLM and handle tool calling loop.

        Args:
            user_message: The user's message
            api_base_url: Base URL for the LMS API
            api_key: API key for the LMS API

        Returns:
            The LLM's final response
        """
        # Initialize conversation with system prompt
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        # Tool calling loop - max 5 iterations to prevent infinite loops
        max_iterations = 5
        for iteration in range(max_iterations):
            self._debug(f"[iteration] Calling LLM (iteration {iteration + 1})")

            response = self._call_llm(messages)

            # Check if LLM wants to call tools
            tool_calls = self._extract_tool_calls(response)

            if not tool_calls:
                # No tool calls - LLM has final answer
                self._debug("[done] LLM provided final answer")
                return self._extract_response_text(response)

            # Execute tool calls
            tool_results = []
            for tool_call in tool_calls:
                result = self._execute_tool(
                    tool_call, api_base_url, api_key
                )
                tool_results.append(result)
                self._debug(f"[tool] Result: {result[:100]}..." if len(result) > 100 else f"[tool] Result: {result}")

            # Feed tool results back to LLM
            self._debug(f"[summary] Feeding {len(tool_results)} tool result(s) back to LLM")

            # Add assistant's tool call to conversation
            assistant_message = {
                "role": "assistant",
                "content": None,
                "tool_calls": tool_calls,
            }
            messages.append(assistant_message)

            # Add tool results to conversation
            for i, result in enumerate(tool_results):
                tool_message = {
                    "role": "tool",
                    "tool_call_id": tool_calls[i].get("id", f"call_{i}"),
                    "content": result,
                }
                messages.append(tool_message)

        # If we get here, we hit max iterations
        return "I'm having trouble answering this question. Please try rephrasing."

    def _call_llm(self, messages: list[dict]) -> dict:
        """Make the actual LLM API call."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "tools": TOOLS,
            "tool_choice": "auto",
        }

        response = self.client.post(
            f"{self.api_base_url}/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    def _extract_tool_calls(self, response: dict) -> list[dict]:
        """Extract tool calls from LLM response."""
        choice = response.get("choices", [{}])[0]
        message = choice.get("message", {})
        tool_calls = message.get("tool_calls", [])

        if tool_calls:
            for tc in tool_calls:
                func = tc.get("function", {})
                self._debug(
                    f"[tool] LLM called: {func.get('name')}({func.get('arguments', {})})"
                )

        return tool_calls

    def _extract_response_text(self, response: dict) -> str:
        """Extract text response from LLM."""
        choice = response.get("choices", [{}])[0]
        message = choice.get("message", {})
        return message.get("content", "")

    def _execute_tool(
        self, tool_call: dict, api_base_url: str, api_key: str
    ) -> str:
        """Execute a tool call and return the result as JSON string."""
        func = tool_call.get("function", {})
        name = func.get("name", "")
        arguments = func.get("arguments", {})

        # Parse arguments if they're a JSON string
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {}

        # Map tool name to API call
        try:
            if name == "get_items":
                result = self._api_get(f"{api_base_url}/items/", api_key)
            elif name == "get_learners":
                result = self._api_get(f"{api_base_url}/learners/", api_key)
            elif name == "get_scores":
                lab = arguments.get("lab", "")
                result = self._api_get(
                    f"{api_base_url}/analytics/scores?lab={lab}", api_key
                )
            elif name == "get_pass_rates":
                lab = arguments.get("lab", "")
                result = self._api_get(
                    f"{api_base_url}/analytics/pass-rates?lab={lab}", api_key
                )
            elif name == "get_timeline":
                lab = arguments.get("lab", "")
                result = self._api_get(
                    f"{api_base_url}/analytics/timeline?lab={lab}", api_key
                )
            elif name == "get_groups":
                lab = arguments.get("lab", "")
                result = self._api_get(
                    f"{api_base_url}/analytics/groups?lab={lab}", api_key
                )
            elif name == "get_top_learners":
                lab = arguments.get("lab", "")
                limit = arguments.get("limit", 5)
                result = self._api_get(
                    f"{api_base_url}/analytics/top-learners?lab={lab}&limit={limit}",
                    api_key,
                )
            elif name == "get_completion_rate":
                lab = arguments.get("lab", "")
                result = self._api_get(
                    f"{api_base_url}/analytics/completion-rate?lab={lab}", api_key
                )
            elif name == "trigger_sync":
                result = self._api_post(f"{api_base_url}/pipeline/sync", {}, api_key)
            else:
                result = json.dumps({"error": f"Unknown tool: {name}"})

            return json.dumps(result)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _api_get(self, url: str, api_key: str) -> Any:
        """Make a GET request to the LMS API."""
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        response = httpx.get(url, headers=headers, timeout=10.0)
        response.raise_for_status()
        return response.json()

    def _api_post(self, url: str, data: dict, api_key: str) -> Any:
        """Make a POST request to the LMS API."""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        } if api_key else {"Content-Type": "application/json"}
        response = httpx.post(url, headers=headers, json=data, timeout=10.0)
        response.raise_for_status()
        return response.json()
