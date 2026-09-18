# Stage 1: Build virtual environment with uv
FROM python:3.12-slim AS builder

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy project files for dependency installation
COPY pyproject.toml uv.lock ./

# Install dependencies using uv into virtual environment
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Stage 2: Final runtime container
FROM python:3.12-slim AS runner

# Install system dependencies (Tesseract OCR, Indonesian pack, curl, nodejs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-ind \
    curl \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtualenv and application code
COPY --from=builder /app/.venv /app/.venv
COPY . /app

# Add virtualenv to PATH so prisma and uvicorn are accessible directly
ENV PATH="/app/.venv/bin:$PATH"

# Run Prisma client generator
RUN prisma generate

# Expose backend port
EXPOSE 8000

# Set entrypoint execution permissions
RUN chmod +x /app/entrypoint.sh

# Run entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]
