#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# ── TODO: project settings ─────────────────────────────────────────────────────
PROJECT_NAME="[Project Name]"
API_PORT=8000        # backend container port
WEB_PORT=3000        # frontend container port
# nginx config name (no spaces)
NGINX_CONF="project.conf"
# Add env vars to auto-set after install. SERVER_IP is replaced with the actual IP.
# Format: "KEY=value" — use SERVER_IP as placeholder for the server's public IP.
# Example (Next.js frontend): "NEXT_PUBLIC_API_URL=http://SERVER_IP/api" "COOKIE_SECURE=false"
ENV_OVERRIDES=()
# ──────────────────────────────────────────────────────────────────────────────

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── 1. root check ─────────────────────────────────────────────────────────────

if [[ $EUID -ne 0 ]]; then
  error "Запусти от root: sudo bash install.sh"
fi

# ── 2. OS check ───────────────────────────────────────────────────────────────

if ! command -v apt-get &>/dev/null; then
  error "Поддерживается только Debian/Ubuntu (apt-get не найден)"
fi

echo
echo -e "${BOLD}========================================"
echo -e "  $PROJECT_NAME — установка сервера"
echo -e "========================================${NC}"
echo -e "  Директория проекта: $PROJECT_DIR"
echo

# ── 3. system packages ────────────────────────────────────────────────────────

info "Обновление пакетов..."
apt-get update -qq

info "Установка базовых пакетов..."
apt-get install -y -qq \
  ca-certificates curl gnupg lsb-release \
  git nginx ufw openssl

# ── 4. Docker CE ──────────────────────────────────────────────────────────────

if command -v docker &>/dev/null; then
  success "Docker уже установлен: $(docker --version)"
else
  info "Установка Docker CE..."
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/$(. /etc/os-release && echo "$ID")/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/$(. /etc/os-release && echo "$ID") \
$(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
  systemctl enable --now docker
  success "Docker установлен"
fi

if ! docker compose version &>/dev/null; then
  error "docker compose plugin не найден — установи вручную"
fi

# ── 5. add deploy user to docker group ────────────────────────────────────────

DEPLOY_USER="${SUDO_USER:-$(logname 2>/dev/null || echo '')}"
if [[ -n "$DEPLOY_USER" && "$DEPLOY_USER" != "root" ]]; then
  usermod -aG docker "$DEPLOY_USER"
  info "Пользователь $DEPLOY_USER добавлен в группу docker (перелогинься после установки)"
fi

# ── 6. .env check ─────────────────────────────────────────────────────────────

if [[ ! -f "$PROJECT_DIR/.env" ]]; then
  error ".env не найден в $PROJECT_DIR — загрузи его на сервер и запусти install.sh снова"
fi
success ".env найден"

# ── 7. get server IP ──────────────────────────────────────────────────────────

SERVER_IP="$(curl -fsSL https://api.ipify.org 2>/dev/null || hostname -I | awk '{print $1}')"
info "IP сервера: $SERVER_IP"

# ── 8. firewall ───────────────────────────────────────────────────────────────

info "Настройка UFW..."
ufw --force reset > /dev/null
ufw default deny incoming > /dev/null
ufw default allow outgoing > /dev/null
ufw allow 22/tcp                          comment 'SSH'           > /dev/null
ufw allow 80/tcp                          comment 'HTTP (nginx)'  > /dev/null
ufw allow "${API_PORT}/tcp"               comment 'API (direct)'  > /dev/null
ufw allow "${WEB_PORT}/tcp"               comment 'Web (direct)'  > /dev/null
ufw --force enable > /dev/null
success "UFW: SSH(22), HTTP(80), API($API_PORT), Web($WEB_PORT)"

# ── 9. nginx ──────────────────────────────────────────────────────────────────

info "Настройка Nginx..."

# TODO: настрой маршруты под свой проект
# Текущая конфигурация: /api/ → API, / → Web
# Добавь location-блоки если нужны особые маршруты (websockets, static, auth и т.д.)
cat > /etc/nginx/sites-available/$NGINX_CONF <<NGINX
server {
    listen 80;
    server_name _;

    client_max_body_size 20m;

    location /api/ {
        proxy_pass         http://127.0.0.1:${API_PORT}/;
        proxy_http_version 1.1;
        proxy_set_header   Host              \$host;
        proxy_set_header   X-Real-IP         \$remote_addr;
        proxy_set_header   X-Forwarded-For   \$proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;
    }

    location / {
        proxy_pass         http://127.0.0.1:${WEB_PORT}/;
        proxy_http_version 1.1;
        proxy_set_header   Host              \$host;
        proxy_set_header   X-Real-IP         \$remote_addr;
        proxy_set_header   Upgrade           \$http_upgrade;
        proxy_set_header   Connection        "upgrade";
    }
}
NGINX

ln -sf /etc/nginx/sites-available/$NGINX_CONF /etc/nginx/sites-enabled/$NGINX_CONF
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable --now nginx
systemctl reload nginx
success "Nginx настроен"

# ── 10. update .env ───────────────────────────────────────────────────────────


info "Обновление .env..."
for pair in "${ENV_OVERRIDES[@]}"; do
  key="${pair%%=*}"
  value="${pair#*=}"
  value="${value//SERVER_IP/$SERVER_IP}"

  if grep -q "^${key}=" "$PROJECT_DIR/.env"; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$PROJECT_DIR/.env"
  else
    echo "${key}=${value}" >> "$PROJECT_DIR/.env"
  fi
done
success ".env обновлён"

# ── 11. permissions ───────────────────────────────────────────────────────────

chmod +x "$PROJECT_DIR/start.sh"
success "start.sh — права выданы"

# ── 12. build ─────────────────────────────────────────────────────────────────

echo
read -rp "  Собрать Docker-образы сейчас? (займёт 5-15 мин) [Y/n]: " BUILD_NOW
BUILD_NOW="${BUILD_NOW:-Y}"
if [[ "$BUILD_NOW" =~ ^[Yy]$ ]]; then
  info "Сборка образов..."
  cd "$PROJECT_DIR"
  DOCKER_BUILDKIT=1 docker compose build
  success "Образы собраны"
fi

# ── 13. summary ───────────────────────────────────────────────────────────────

echo
echo -e "${GREEN}${BOLD}========================================"
echo -e "  Установка завершена!"
echo -e "========================================${NC}"
echo
echo -e "  Проект:    ${BOLD}$PROJECT_DIR${NC}"
echo -e "  Сервер:    ${BOLD}http://${SERVER_IP}${NC}"
echo
echo -e "  Web:  http://${SERVER_IP}              (через nginx)"
echo -e "  API:  http://${SERVER_IP}/api/         (через nginx)"
echo -e "  API:  http://${SERVER_IP}:${API_PORT}  (напрямую)"
echo
echo -e "  ${YELLOW}Следующий шаг:${NC}"
echo -e "  cd $PROJECT_DIR && bash start.sh  → выбери 1) Запуск"
echo
if [[ -n "$DEPLOY_USER" && "$DEPLOY_USER" != "root" ]]; then
  echo -e "  ${YELLOW}Важно:${NC} перелогинься как $DEPLOY_USER перед запуском start.sh"
  echo -e "  (иначе docker потребует sudo)"
  echo
fi
