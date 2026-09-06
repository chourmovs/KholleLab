FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/* \
    && addgroup --system app && adduser --system --ingroup app app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/alembic.ini ./
COPY backend/alembic ./alembic
COPY backend/app ./app
COPY --chmod=755 backend/docker-entrypoint.sh /usr/local/bin/docker-entrypoint
COPY problems /problems
COPY resources /resources
RUN mkdir -p /runtime-logs && chown app:app /runtime-logs
ENTRYPOINT ["docker-entrypoint"]
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=6 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"]
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
