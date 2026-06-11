FROM python:3.12-slim

RUN useradd -m -u 1000 appuser
WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv globally
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv

COPY --chown=appuser:appuser . .

# Ensure upload directories exist and are owned by appuser
RUN mkdir -p uploads/submissions && chown -R appuser:appuser uploads

# Increase timeout for slow connections
ENV UV_HTTP_TIMEOUT=500
# Sync dependencies from lockfile
RUN uv sync --frozen

# Add virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"

USER appuser

# API port (defaults to 8000, overridable via BACKEND_PORT env).
ARG BACKEND_PORT=8000
ENV BACKEND_PORT=${BACKEND_PORT}

EXPOSE ${BACKEND_PORT}

CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${BACKEND_PORT}

