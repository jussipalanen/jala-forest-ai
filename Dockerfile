# Map app image: Streamlit behind a Caddy proxy (crawler blocking, health check, optional login).
# Reads the GeoParquet export baked in at build time; it does not need PostGIS.
FROM caddy:2.11.8-alpine AS caddy

FROM python:3.15-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /bin/uv
COPY --from=caddy /usr/bin/caddy /usr/bin/caddy

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    DATA_PATH=/app/data/export/stand_natura_overlap.parquet \
    XDG_CONFIG_HOME=/tmp \
    XDG_DATA_HOME=/tmp

WORKDIR /app

# Dependencies first for better layer caching. Only the app's own dependencies:
# the import/PostGIS group and the dev tools are left out.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-default-groups --no-install-project

COPY src ./src
COPY app ./app
COPY .streamlit ./.streamlit
RUN uv sync --frozen --no-default-groups

COPY docker/proxy/Caddyfile /etc/caddy/Caddyfile
COPY docker/proxy/entrypoint.sh /usr/local/bin/entrypoint.sh
# The data the map shows (produced by `./dev run`). Docker Compose mounts a fresh copy over it.
COPY data/export/stand_natura_overlap.parquet ./data/export/stand_natura_overlap.parquet

RUN useradd --create-home --uid 10001 appuser
USER appuser

# Cloud Run sends traffic to $PORT; Caddy listens there and proxies to Streamlit on 8502.
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
