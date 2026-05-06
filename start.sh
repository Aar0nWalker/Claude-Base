#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ── TODO: project settings ─────────────────────────────────────────────────────
PROJECT_NAME="[Project Name]"
# Health check endpoint inside container (adjust path if needed)
HEALTH_CHECK_URL="http://localhost:8000/health"
# TODO: add other project-specific vars here
# ──────────────────────────────────────────────────────────────────────────────

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

cd "$PROJECT_DIR"

wait_for_api() {
  info "Ожидание запуска API..."
  until docker compose exec -T api python -c \
    "import urllib.request; urllib.request.urlopen('$HEALTH_CHECK_URL')" &>/dev/null; do
    sleep 3
  done
  success "API готов"
}

show_menu() {
  clear
  echo -e "${BOLD}========================================${NC}"
  echo -e "${BOLD}  $PROJECT_NAME — Docker Control${NC}"
  echo -e "${BOLD}========================================${NC}"
  echo
  echo "  1) Запуск проекта"
  echo "  2) Остановка проекта"
  echo "  3) Перезапуск проекта"
  echo "  4) Пересборка проекта"
  echo "  5) Логи"
  echo "  6) Очистка проекта"
  echo "  7) Выход"
  echo
}

do_start() {
  info "Запуск проекта..."
  docker compose up -d
  success "Проект запущен"
}

do_stop() {
  info "Остановка проекта..."
  docker compose down --remove-orphans
  success "Проект остановлен"
}

do_restart() {
  info "Перезапуск проекта..."
  docker compose down --remove-orphans
  docker compose up -d
  success "Проект перезапущен"
}

do_rebuild() {
  info "Пересборка образов..."
  docker compose down --remove-orphans
  if ! docker compose build; then
    error "Сборка завершилась с ошибкой. Исправь ошибки и попробуй снова."
    return 1
  fi
  docker compose up -d
  wait_for_api
  info "Запуск тестов..."
  if ! docker compose exec -T api sh -c 'pytest --tb=short -q'; then
    warn "Некоторые тесты упали. Проверь вывод выше."
    read -rp "  Продолжить? [Y/n]: " cont
    if [[ "$cont" =~ ^[Nn]$ ]]; then return 1; fi
  fi
  # TODO: раскомментируй если есть seed-скрипт
  # info "Наполнение базы данных..."
  # docker compose exec -T api python seed.py
  success "Проект пересобран и запущен"
}

do_logs() {
  clear
  echo -e "${BOLD}========================================${NC}"
  echo -e "${BOLD}  Логи (Ctrl+C для остановки)${NC}"
  echo -e "${BOLD}========================================${NC}"
  echo
  # TODO: добавь/убери сервисы под свой docker-compose.yml
  echo "  1) Все сервисы"
  echo "  2) API"
  echo "  3) Web"
  echo "  4) DB"
  echo "  5) Redis"
  echo "  6) Назад"
  echo
  read -rp "  Выбор [1-6]: " log_choice
  echo
  case "$log_choice" in
    1) docker compose logs -f ;;
    2) docker compose logs -f api ;;
    3) docker compose logs -f web ;;
    4) docker compose logs -f db ;;
    5) docker compose logs -f redis ;;
    6) return ;;
    *) warn "Неверный выбор" ;;
  esac
}

do_cleanup() {
  clear
  echo -e "${BOLD}========================================${NC}"
  echo -e "${BOLD}  ОЧИСТКА ПРОЕКТА${NC}"
  echo -e "${BOLD}========================================${NC}"
  echo
  echo "  Удаляет: контейнеры, тома, сети,"
  echo "  образы проекта и все dangling-образы."
  echo -e "  ${RED}ВСЕ ДАННЫЕ БАЗЫ БУДУТ УДАЛЕНЫ.${NC}"
  echo
  read -rp "  Продолжить? [y/N]: " confirm
  if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    info "Отмена"
    return
  fi
  info "[1/3] Удаление контейнеров, томов, сетей и образов..."
  docker compose down --remove-orphans -v --rmi local
  info "[2/3] Удаление dangling-образов..."
  docker images -f "dangling=true" -q | xargs -r docker rmi || true
  info "[3/3] Удаление неиспользуемых томов..."
  docker volume prune -f
  success "Очистка завершена. Все данные проекта удалены."
}

if [[ "${1:-}" == "--rebuild" ]]; then
    do_rebuild
    exit $?
fi

show_menu
read -rp "  Выбор действия [1-7]: " choice
echo
case "$choice" in
  1) do_start ;;
  2) do_stop ;;
  3) do_restart ;;
  4) do_rebuild ;;
  5) do_logs ;;
  6) do_cleanup ;;
  7) ;;
  *) warn "Неверный выбор" ;;
esac
