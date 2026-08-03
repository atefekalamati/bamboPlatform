FROM python:3.13-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.lock .
RUN pip install --upgrade pip && pip install --require-hashes -r requirements.lock

FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_ENV=production
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       fonts-noto-core libharfbuzz-subset0 libpango-1.0-0 libpangoft2-1.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 bambo \
    && useradd --system --uid 10001 --gid bambo --home-dir /app bambo \
    && mkdir -p /data/dwg \
    && chown -R bambo:bambo /app /data/dwg
COPY --from=builder /opt/venv /opt/venv
COPY --chown=bambo:bambo app ./app
COPY --chown=bambo:bambo alembic ./alembic
COPY --chown=bambo:bambo alembic.ini ./alembic.ini
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=3)"
CMD ["sh", "-c", "exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WEB_CONCURRENCY:-1} --proxy-headers --forwarded-allow-ips ${FORWARDED_ALLOW_IPS:?FORWARDED_ALLOW_IPS is required}"]
