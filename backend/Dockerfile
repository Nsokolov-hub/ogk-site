FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# The API is reached through Caddy on a private Docker network. X-Forwarded-For is trusted only from those
# hops, so request.client is the real visitor (rate limits, consent evidence) and cannot be spoofed.
ENV FORWARDED_ALLOW_IPS="127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"
ENV STORAGE_DIR=/data/files
WORKDIR /app
RUN groupadd --gid 10001 site && useradd --uid 10001 --gid site --create-home site \
    && mkdir -p /data/files && chown site:site /data/files
# Runtime dependencies only; tests and linters are pinned separately in requirements-dev.lock.
COPY requirements.lock ./requirements.lock
RUN pip install --no-cache-dir -r requirements.lock
COPY --chown=site:site . .
USER site
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--proxy-headers"]
