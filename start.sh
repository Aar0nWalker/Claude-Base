#!/usr/bin/env bash
# {{PROJECT_NAME}} — Docker control (Linux/macOS).
# Menu: start / stop / restart / rebuild / logs / cleanup / rollback.
# `start.sh --rebuild` and `start.sh --rollback` run non-interactively (used by deploy.sh).
#
# ponytail: rolling rebuild (build new images while the old site stays up, then
# recreate api/worker/web) + /health smoke check. No blue-green / queue-drain —
# add that per-project only if you have long-running jobs that must not be killed.
set -Eeuo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

PROJECT_NAME="{{PROJECT_NAME}}"
PROJECT_SLUG="{{PROJECT_SLUG}}"
HEALTH_WEB_URL="http://localhost:3001"
HEALTH_API_URL="http://localhost:8000/health"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE="docker compose"
export DOCKER_BUILDKIT=1
cd "$PROJECT_DIR"

image_exists() { docker image inspect "$1" >/dev/null 2>&1; }

wait_for_url() {
  local name="$1" url="$2" tries="${3:-60}" delay="${4:-2}"
  info "Ожидание $name..."
  for _ in $(seq 1 "$tries"); do
    if curl -fsS "$url" >/dev/null 2>&1; then success "$name готов"; return 0; fi
    sleep "$delay"
  done
  error "$name не ответил: $url"; return 1
}

ensure_dirs() { mkdir -p "$PROJECT_DIR/backups"; }

snapshot_for_rollback() {
  for svc in web api worker; do
    if image_exists "${PROJECT_SLUG}-${svc}:latest"; then
      docker image tag "${PROJECT_SLUG}-${svc}:latest" "${PROJECT_SLUG}-${svc}:rollback"
    fi
  done
}

do_start()   { info "Запуск..."; ensure_dirs; $COMPOSE up -d; success "Запущено"; }
do_stop()    { info "Остановка..."; $COMPOSE down --remove-orphans; success "Остановлено"; }
do_restart() { info "Перезапуск..."; ensure_dirs; $COMPOSE down --remove-orphans; $COMPOSE up -d; success "Перезапущено"; }

do_rebuild() {
  info "Пересборка образов (сайт остаётся поднятым во время сборки)..."
  ensure_dirs
  snapshot_for_rollback
  # Build serially: parallel builds spike memory (npm ci + pip) and can OOM.
  $COMPOSE build web || { error "Сборка web упала."; return 1; }
  $COMPOSE build api worker-fast || { error "Сборка api/worker упала."; return 1; }
  info "Пересоздание api/worker/web с новыми образами..."
  $COMPOSE up -d --no-deps api worker-fast
  wait_for_url "API" "$HEALTH_API_URL" 60 2
  $COMPOSE up -d --no-deps web
  wait_for_url "Web" "$HEALTH_WEB_URL" 80 3
  info "Чистка build-cache (держим ≤8 ГБ)..."
  docker builder prune -f --keep-storage "${BUILD_CACHE_KEEP_STORAGE:-8GB}" >/dev/null 2>&1 || true
  success "Пересобрано и запущено"
}

do_rollback() {
  info "Откат на предыдущие образы (:rollback)..."
  ensure_dirs
  for svc in web api worker; do
    image_exists "${PROJECT_SLUG}-${svc}:rollback" || { error "Нет ${PROJECT_SLUG}-${svc}:rollback — сначала нужен хотя бы один успешный деплой."; return 1; }
  done
  local failed_tag="failed-$(date -u +%Y%m%d%H%M%S)"
  for svc in web api worker; do
    image_exists "${PROJECT_SLUG}-${svc}:latest" && docker image tag "${PROJECT_SLUG}-${svc}:latest" "${PROJECT_SLUG}-${svc}:${failed_tag}" || true
    docker image tag "${PROJECT_SLUG}-${svc}:rollback" "${PROJECT_SLUG}-${svc}:latest"
  done
  $COMPOSE up -d --no-deps --no-build api worker-fast
  wait_for_url "API" "$HEALTH_API_URL" 60 2
  $COMPOSE up -d --no-deps --no-build web
  wait_for_url "Web" "$HEALTH_WEB_URL" 80 3
  success "Откат завершён. Прошлая версия сохранена как :${failed_tag}."
}

do_logs() {
  echo "  1) Все сервисы   2) Web   3) API   4) Worker   5) Назад"
  read -rp "  Выбор: " c
  case "$c" in
    1) $COMPOSE logs -f ;;
    2) $COMPOSE logs -f web ;;
    3) $COMPOSE logs -f api ;;
    4) $COMPOSE logs -f worker-fast ;;
    *) return ;;
  esac
}

do_cleanup() {
  warn "Удалит контейнеры, тома, сети и образы проекта. ВСЕ ДАННЫЕ БУДУТ УДАЛЕНЫ."
  read -rp "  Продолжить? [y/N]: " confirm
  [[ "$confirm" =~ ^[Yy]$ ]] || { info "Отмена"; return; }
  $COMPOSE down --remove-orphans -v --rmi local
  docker volume prune -f
  success "Очистка завершена."
}

case "${1:-}" in
  --rebuild)  do_rebuild;  exit $? ;;
  --rollback) do_rollback; exit $? ;;
esac

clear
echo -e "${BOLD}  $PROJECT_NAME — Docker Control${NC}"
echo "  1) Запуск   2) Остановка   3) Перезапуск   4) Пересборка"
echo "  5) Логи     6) Очистка     7) Откат        8) Выход"
read -rp "  Выбор [1-8]: " choice
case "$choice" in
  1) do_start ;; 2) do_stop ;; 3) do_restart ;; 4) do_rebuild ;;
  5) do_logs ;; 6) do_cleanup ;; 7) do_rollback ;; 8) ;;
  *) warn "Неверный выбор" ;;
esac
