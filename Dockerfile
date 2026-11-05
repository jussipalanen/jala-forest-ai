# Streamlit map app. Reads the GeoParquet export from DATA_PATH; it does not need PostGIS.
FROM python:3.15-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PORT=8501 \
    DATA_PATH=/app/data/export/stand_natura_overlap.parquet

WORKDIR /app

# Dependencies first for better layer caching.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY app ./app
COPY .streamlit ./.streamlit
RUN uv sync --frozen --no-dev

RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8501
# PORT is honoured so the same image can run on Cloud Run.
CMD ["sh", "-c", "streamlit run app/streamlit_app.py --server.headless true --server.address 0.0.0.0 --server.port ${PORT}"]
