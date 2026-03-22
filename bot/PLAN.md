# LMS Telegram Bot — Implementation Plan

## Overview

This document outlines the implementation plan for building a Telegram bot that lets users interact with the LMS backend through chat. The bot supports slash commands like `/health` and `/labs`, and uses an LLM to understand plain language questions.

## Architecture

The bot follows a **layered architecture** with clear separation of concerns:

```
bot/
├── bot.py              # Entry point (Telegram startup + --test mode)
├── config.py           # Environment variable loading
├── handlers/           # Command handlers (no Telegram dependency)
│   ├── start.py        # /start handler
│   ├── help.py         # /help handler
│   ├── health.py       # /health handler
│   ├── labs.py         # /labs handler
│   └── scores.py       # /scores handler
└── services/           # External service clients
    ├── api_client.py   # LMS API client
    └── llm_client.py   # LLM client for intent routing
```

### Key Design Decisions

1. **Testable Handlers**: Command handlers are plain functions that take input and return text. They have no dependency on Telegram, which means:
   - They can be tested via `--test` mode without a Telegram connection
   - They can be unit tested in isolation
   - The same handler works from Telegram, test mode, or future interfaces

2. **Configuration via Environment**: All secrets (bot token, API keys) are loaded from `.env.bot.secret` using pydantic-settings. This keeps secrets out of code and makes deployment configuration straightforward.

3. **Error Handling**: All external calls (API, LLM) are wrapped with try/except blocks that return user-friendly messages instead of crashing.

## Task 1: Plan and Scaffold

**Goal**: Create project structure with testable handler architecture and `--test` mode.

**Approach**:
- Create `bot/` directory with entry point `bot.py`
- Implement `--test` mode that calls handlers directly and prints to stdout
- Create handler modules for `/start`, `/help`, `/health`, `/labs`, `/scores`
- Each handler returns placeholder text initially
- Set up `pyproject.toml` with dependencies (aiogram, httpx, pydantic-settings)

**Acceptance**:
- `uv run bot.py --test "/start"` prints welcome message
- All P0 commands return non-empty output without crashing

## Task 2: Backend Integration

**Goal**: Connect handlers to the real LMS backend API.

**Approach**:
- Create `services/api_client.py` with a `LmsApiClient` class
- Implement Bearer token authentication using `LMS_API_KEY`
- Update handlers to call real endpoints:
  - `/health` → `GET /health`
  - `/labs` → `GET /items/` (filter for type=lab)
  - `/scores` → `GET /analytics/pass-rates?lab=<name>`
- Handle API errors gracefully (unreachable, timeout, auth failures)

**Acceptance**:
- `/health` reports actual backend status
- `/labs` lists real labs from the backend
- `/scores` shows pass rates for specified lab

## Task 3: Intent-Based Natural Language Routing

**Goal**: Enable plain text questions interpreted by an LLM.

**Approach**:
- Create `services/llm_client.py` with tool definitions for each API endpoint
- Each tool has a description that tells the LLM when to use it
- Implement intent router that:
  1. Sends user message + tool descriptions to LLM
  2. LLM decides which tool to call based on descriptions
  3. Bot executes the tool and returns result
- Tools wrap the same API calls from Task 2

**Key Insight**: The LLM reads tool descriptions to decide what to call. Description quality matters more than prompt engineering. If the LLM picks the wrong tool, improve the description — don't add regex routing.

**Acceptance**:
- "what labs are available" → calls labs tool
- "check system health" → calls health tool
- "show scores for lab 01" → calls scores tool

## Task 4: Containerize and Document

**Goal**: Deploy bot alongside backend using Docker Compose.

**Approach**:
- Create `bot/Dockerfile` based on Python 3.14
- Add bot service to `docker-compose.yml`
- Configure networking so bot can reach backend via service name (not localhost)
- Update config to support both local and Docker environments
- Document deployment in README

**Docker Networking**: Containers use service names (e.g., `backend`) as hostnames, not `localhost`. The bot's `LMS_API_BASE_URL` must be set to `http://backend:42002` in Docker.

**Acceptance**:
- `docker compose up` starts both backend and bot
- Bot responds to commands in Telegram
- README documents deployment steps

## Testing Strategy

1. **Test Mode**: Every command can be tested offline via `--test` flag
2. **Unit Tests**: Handlers can be tested in isolation (future work)
3. **Integration Tests**: Test full flow from Telegram to backend (future work)

## Deployment Checklist

- [ ] `.env.bot.secret` exists on VM with `BOT_TOKEN`, `LMS_API_KEY`, `LLM_API_KEY`
- [ ] Backend is running and accessible
- [ ] Bot container starts without errors
- [ ] Bot responds to `/start` in Telegram
- [ ] Bot responds to plain language questions
