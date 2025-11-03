FROM python:3.11-slim

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

# Use uv to install - much faster than pip
RUN uv pip install --system --no-cache-dir .

USER appuser

EXPOSE 8000

CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000

