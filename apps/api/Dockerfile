# Cognexa API container. Build from the REPOSITORY ROOT so the subject data is included:
#   docker build -f apps/api/Dockerfile -t cognexa-api .
# Layout inside the image mirrors the repo (/srv/apps/api, /srv/data) because the app finds
# data/subjects relative to its own source tree (app/graph/loader.py).

# ---- build stage: resolve and install locked dependencies with uv ----
FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.11.28 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/srv/.venv
WORKDIR /srv/apps/api
# Dependencies first (cached layer), then the app itself.
COPY apps/api/pyproject.toml apps/api/uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY apps/api/app ./app
RUN uv sync --locked --no-dev

# ---- runtime stage: no uv, no build tools, non-root ----
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/srv/.venv/bin:$PATH" \
    APP_ENV=production \
    PORT=8000
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /srv --shell /usr/sbin/nologin app
WORKDIR /srv/apps/api
COPY --from=build --chown=app:app /srv/.venv /srv/.venv
COPY --from=build --chown=app:app /srv/apps/api /srv/apps/api
COPY --chown=app:app data /srv/data
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", \"8000\")}/health', timeout=4)"]
# One worker: the free instance has 512 MB, and rate limits/caches live in process memory.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1 --proxy-headers --forwarded-allow-ips='*' --no-server-header"]
