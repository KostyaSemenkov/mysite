#!/usr/bin/env bash
# Деплой «Досок», когда сервер не может скачать пакеты npm: фронтенд собирается
# локально, на сервер уезжает готовая сборка (frontend/dist), образ собирается
# там без обращения к реестру (стадия app-prebuilt в boardapp/Dockerfile).
#
#   scripts/deploy_boards_prebuilt.sh [хост ssh] [каталог проекта на сервере]
#
# По умолчанию: хост vm-lemurqa, каталог ~/mysite. Текущая ветка должна быть
# запушена: на сервере выполняется git pull.
set -euo pipefail

cd "$(dirname "$0")/.."
HOST="${1:-vm-lemurqa}"
REMOTE_DIR="${2:-~/mysite}"
COMPOSE="sudo docker compose -f docker-compose.yml -f docker-compose.prebuilt.yml"

echo "» сборка фронтенда"
(cd boardapp/frontend && npm ci && npm run build)

echo "» передача dist на $HOST"
tar czf /tmp/boards-dist.tgz -C boardapp/frontend dist
scp -q /tmp/boards-dist.tgz "$HOST:/tmp/boards-dist.tgz"
rm -f /tmp/boards-dist.tgz

echo "» сборка образа и перезапуск на сервере"
# Коды возврата проверяются явно: конвейер через tail маскировал бы ошибку сборки.
ssh "$HOST" "set -e; cd $REMOTE_DIR && git pull -q \
  && tar xzf /tmp/boards-dist.tgz -C boardapp/frontend && rm -f /tmp/boards-dist.tgz \
  && $COMPOSE build boards \
  && $COMPOSE up -d --no-build boards \
  && sudo docker compose ps --format '{{.Service}} {{.Status}}'"
