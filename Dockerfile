# Use a slim Python 3.11 builder to keep images extremely compact
FROM python:3.11-slim-bookworm AS builder
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Final Execution Stage
FROM python:3.11-slim-bookworm
# Install curl for healthchecks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app
# Copy compiled dependencies
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .

# Expose the internal API port (8000) and public UI port (7860)
EXPOSE 8000
EXPOSE 7860

# Launch the OpenEnv-compatible API server
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
