FROM python:3.14.2-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy root-level project files for workspace sync
COPY pyproject.toml uv.lock ./

# Copy bot project files
COPY bot/pyproject.toml ./bot/

# Install dependencies using uv (syncs entire workspace)
RUN uv sync --frozen

# Copy bot source code
COPY bot/ ./bot/

# Run the bot
CMD ["uv", "run", "bot/bot.py"]
