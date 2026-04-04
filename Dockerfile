# Use a slim Python 3.11 builder to keep images extremely compact
FROM python:3.11-slim-bookworm AS builder
# Set optimal environmental variables to prevent unnecessary cache bloat
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app
# Install only what we exactly need layer-by-layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# ==============================================================================
# Final Execution Stage
# Highly Optimized for Scalar x Meta 2 vCPU / 8 GB RAM Limit!
# ==============================================================================
FROM python:3.11-slim-bookworm
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1
WORKDIR /app
# Safely copy only compiled dependencies
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
# Copy simulator environment payloads
COPY . .
# Keep the container alive indefinitely so the OpenEnv orchestrator can import the environment variables and execute tasks
CMD ["tail", "-f", "/dev/null"]
