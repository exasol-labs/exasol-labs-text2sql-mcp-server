FROM python:3.13-slim AS build

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install poetry

WORKDIR /app

COPY pyproject.toml poetry.lock README.md ./
COPY exasol_mcp_server_governed_sql/ ./exasol_mcp_server_governed_sql/

RUN poetry build

FROM python:3.13-slim

WORKDIR /app
COPY --from=build app/dist dist

RUN pip install dist/*.whl





EXPOSE 9100

ENTRYPOINT ["exasol-mcp-server-governed-sql-http"]
CMD ["--host", "0.0.0.0", "--port", "9100"]