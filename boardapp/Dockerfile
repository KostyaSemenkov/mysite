FROM node:22-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
# Кэш npm живёт между сборками (cache mount BuildKit): реестр периодически отвечает
# серверу 403 или таймаутом на часть файлов, и тогда очередная попытка догружает
# только недостающее вместо полной загрузки. Без --silent, чтобы причина падения
# была видна в логе сборки.
RUN --mount=type=cache,target=/root/.npm \
    npm ci --no-audit --no-fund --loglevel=error \
      --fetch-retries=5 --fetch-retry-mintimeout=2000 --fetch-retry-maxtimeout=30000
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app/backend

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

EXPOSE 8000
# The WebSocket rooms and their change locks are shared within one process.
# --ws-max-size: лимит одного сообщения сокета (256 КБ) — защита от oversized-кадров.
CMD ["sh", "-c", "python -m alembic upgrade head && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --ws-max-size 262144"]

# Фронтенд, собранный заранее (локально: npm ci && npm run build в frontend/), — для
# сервера, которому недоступен реестр npm. Папка dist передаётся дополнительным
# контекстом; сборка и запуск описаны в docker-compose.prebuilt.yml.
FROM runtime AS app-prebuilt
COPY --from=dist dist /app/frontend/dist

# Полная сборка (по умолчанию): фронтенд собран на этапах выше.
FROM runtime AS app
COPY --from=frontend /app/frontend/dist /app/frontend/dist
