FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Create necessary directories upfront
# This prevents the 'Permission Denied' / 'File Not Found' errors
RUN mkdir -p /data/vectordb /app/logs

# Install the package (pin fastmcp < 3 as recommended in startup logs)
RUN uv pip install exasol-mcp-server-governed-sql

EXPOSE 9100

ENTRYPOINT ["exasol-mcp-server-governed-sql-http"]
CMD ["--host", "0.0.0.0", "--port", "9100"]