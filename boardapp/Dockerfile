FROM node:22-alpine AS frontend
# В контейнере сборки IPv6 может не маршрутизироваться: Node первым пробует AAAA-адрес
# реестра и ловит ETIMEDOUT на части пакетов. Сначала IPv4 — сборка стабильна.
ENV NODE_OPTIONS=--dns-result-order=ipv4first
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --silent
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app/backend

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

COPY --from=frontend /app/frontend/dist /app/frontend/dist

EXPOSE 8000
# The WebSocket rooms and their change locks are shared within one process.
# --ws-max-size: лимит одного сообщения сокета (256 КБ) — защита от oversized-кадров.
CMD ["sh", "-c", "python -m alembic upgrade head && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --ws-max-size 262144"]
