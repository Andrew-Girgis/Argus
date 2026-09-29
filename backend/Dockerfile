FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --locked --no-dev --no-install-project

# Copy application code
COPY app/ app/

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=5 \
    CMD ["uv", "run", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
