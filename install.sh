#!/usr/bin/env bash
# {{PROJECT_NAME}} — first-time server setup (Debian/Ubuntu, run as root).
# Installs Docker CE + nginx + ufw + certbot, configures firewall, generates the
# nginx config (/ → web, /backend/ → api, optional /media/ → S3), issues TLS,
# binds app ports to localhost, then optionally builds the Docker images.
#
# Usage: sudo bash install.sh
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# ── Project settings (init.md fills these) ─────────────────────────────────────
PROJECT_NAME="{{PROJECT_NAME}}"
API_PORT=8000
WEB_PORT=3001
NGINX_CONF="{{PROJECT_SLUG}}.conf"
DOMAIN="{{DOMAIN}}"
DOMAIN_WWW="www.${DOMAIN}"
LE_EMAIL=""   # empty → taken from .env ADMIN_EMAIL, fallback admin@$DOMAIN
# Env vars auto-set after install. SERVER_IP is replaced with the real IP.
# CDN_BASE is only used if you serve media through your own domain (nginx /media/ → S3).
ENV_OVERRIDES=("CDN_BASE=https://${DOMAIN}/media")
# ──────────────────────────────────────────────────────────────────────────────

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

[[ $EUID -ne 0 ]] && error "Запусти от root: sudo bash install.sh"
command -v apt-get &>/dev/null || error "Поддерживается только Debian/Ubuntu"

echo; echo -e "${BOLD}  $PROJECT_NAME — установка сервера${NC}"; echo "  Директория: $PROJECT_DIR"; echo

info "Установка базовых пакетов..."
apt-get update -qq
apt-get install -y -qq ca-certificates curl gnupg lsb-release git nginx ufw openssl dnsutils certbot python3-certbot-nginx

if command -v docker &>/dev/null; then
  success "Docker уже установлен: $(docker --version)"
else
  info "Установка Docker CE..."
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/$(. /etc/os-release && echo "$ID")/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$(. /etc/os-release && echo "$ID") $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
  systemctl enable --now docker
  success "Docker установлен"
fi
docker compose version &>/dev/null || error "docker compose plugin не найден"

# Docker daemon: bigger build cache + reliable DNS for build containers (apt in
# builds fails on flaky host DNS). Merged idempotently; restart only on change.
DAEMON_JSON="/etc/docker/daemon.json"
if command -v python3 &>/dev/null; then
  CHANGED="$(python3 - "$DAEMON_JSON" <<'PY'
import json, os, sys
path = sys.argv[1]
try:
    cfg = json.load(open(path))
    if not isinstance(cfg, dict): cfg = {}
except Exception:
    cfg = {}
gc = cfg.setdefault("builder", {}).setdefault("gc", {})
changed = gc.get("defaultKeepStorage") != "8GB" or gc.get("enabled") is not True
gc["enabled"] = True; gc["defaultKeepStorage"] = "8GB"
if not cfg.get("dns"):
    cfg["dns"] = ["8.8.8.8", "1.1.1.1"]; changed = True
os.makedirs(os.path.dirname(path), exist_ok=True)
json.dump(cfg, open(path, "w"), indent=2)
print("CHANGED" if changed else "UNCHANGED")
PY
)"
  [[ "$CHANGED" == "CHANGED" ]] && systemctl is-active --quiet docker && { systemctl restart docker || warn "Не смог перезапустить docker"; success "Docker: кэш 8GB + DNS"; }
fi

DEPLOY_USER="${SUDO_USER:-$(logname 2>/dev/null || echo '')}"
if [[ -n "$DEPLOY_USER" && "$DEPLOY_USER" != "root" ]]; then
  usermod -aG docker "$DEPLOY_USER"
  info "Пользователь $DEPLOY_USER добавлен в группу docker (перелогинься после установки)"
fi

[[ -f "$PROJECT_DIR/.env" ]] || error ".env не найден в $PROJECT_DIR — загрузи его и запусти снова"
success ".env найден"

SERVER_IP="$(curl -fsSL https://api.ipify.org 2>/dev/null || hostname -I | awk '{print $1}')"
info "IP сервера: $SERVER_IP"

info "Настройка UFW (SSH + 80 + 443)..."
ufw --force reset > /dev/null
ufw default deny incoming > /dev/null
ufw default allow outgoing > /dev/null
ufw allow 22/tcp  comment 'SSH'   > /dev/null
ufw allow 80/tcp  comment 'HTTP'  > /dev/null
ufw allow 443/tcp comment 'HTTPS' > /dev/null
ufw --force enable > /dev/null
success "UFW настроен"

# Optional /media/ → S3 proxy (only if S3_ENDPOINT + S3_BUCKET set in .env).
S3_ENDPOINT_V="$(grep -E '^S3_ENDPOINT=' "$PROJECT_DIR/.env" | head -1 | cut -d= -f2- || true)"
S3_BUCKET_V="$(grep -E '^S3_BUCKET=' "$PROJECT_DIR/.env" | head -1 | cut -d= -f2- || true)"
S3_ENDPOINT_V="${S3_ENDPOINT_V//[\"\' ]/}"; S3_BUCKET_V="${S3_BUCKET_V//[\"\' ]/}"
MEDIA_LOCATION=""
if [[ -n "$S3_ENDPOINT_V" && -n "$S3_BUCKET_V" ]]; then
  S3_HOST="${S3_ENDPOINT_V#*://}"; S3_HOST="${S3_HOST%%/*}"
  MEDIA_LOCATION="
    location /media/ {
        proxy_pass         ${S3_ENDPOINT_V%/}/${S3_BUCKET_V}/;
        proxy_set_header   Host ${S3_HOST};
        proxy_ssl_server_name on;
        proxy_hide_header  Set-Cookie;
        add_header         Cache-Control \"public, max-age=31536000, immutable\" always;
    }
"
fi

info "Настройка Nginx..."
cat > /etc/nginx/sites-available/$NGINX_CONF <<NGINX
server {
    listen 80;
    server_name ${DOMAIN} ${DOMAIN_WWW};
    client_max_body_size 50m;

    location /backend/ {
        proxy_pass         http://127.0.0.1:${API_PORT}/;
        proxy_http_version 1.1;
        proxy_set_header   Host              \$host;
        proxy_set_header   X-Real-IP         \$remote_addr;
        proxy_set_header   X-Forwarded-For   \$proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }

    location / {
        proxy_pass         http://127.0.0.1:${WEB_PORT}/;
        proxy_http_version 1.1;
        proxy_set_header   Host              \$host;
        proxy_set_header   X-Real-IP         \$remote_addr;
        proxy_set_header   X-Forwarded-For   \$proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto \$scheme;
        proxy_set_header   Upgrade           \$http_upgrade;
        proxy_set_header   Connection        "upgrade";
        proxy_read_timeout 120s;
    }
${MEDIA_LOCATION}
}
NGINX

ln -sf /etc/nginx/sites-available/$NGINX_CONF /etc/nginx/sites-enabled/$NGINX_CONF
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable --now nginx
systemctl reload nginx
success "Nginx настроен (${DOMAIN})"

info "Настройка HTTPS (Let's Encrypt)..."
if [[ -z "$LE_EMAIL" ]]; then
  LE_EMAIL="$(grep -E '^ADMIN_EMAIL=' "$PROJECT_DIR/.env" | head -1 | cut -d= -f2- || true)"
  LE_EMAIL="${LE_EMAIL//[\"\' ]/}"
fi
[[ -z "$LE_EMAIL" ]] && LE_EMAIL="admin@${DOMAIN}"
DOMAIN_IP="$(dig +short A "$DOMAIN" | tail -1 || true)"
if [[ "$DOMAIN_IP" == "$SERVER_IP" ]]; then
  if certbot --nginx -d "$DOMAIN" -d "$DOMAIN_WWW" --non-interactive --agree-tos -m "$LE_EMAIL" --redirect; then
    systemctl reload nginx; success "HTTPS включён: https://${DOMAIN}"
  else
    warn "Сертификат не выпущен — сайт по HTTP. Повтори: certbot --nginx -d $DOMAIN -d $DOMAIN_WWW -m $LE_EMAIL --agree-tos --redirect"
  fi
else
  warn "A-запись $DOMAIN ($DOMAIN_IP) ≠ сервер ($SERVER_IP). Настрой DNS, затем: certbot --nginx -d $DOMAIN -d $DOMAIN_WWW -m $LE_EMAIL --agree-tos --redirect"
fi

# Bind app ports to localhost (Docker bypasses UFW). Idempotent.
COMPOSE="$PROJECT_DIR/docker-compose.yml"
if [[ -f "$COMPOSE" ]]; then
  sed -i -E 's#^(\s*-\s*)"3001:3000"#\1"127.0.0.1:3001:3000"#' "$COMPOSE"
  sed -i -E 's#^(\s*-\s*)"8000:8000"#\1"127.0.0.1:8000:8000"#' "$COMPOSE"
fi

info "Обновление .env..."
for pair in "${ENV_OVERRIDES[@]}"; do
  key="${pair%%=*}"; value="${pair#*=}"; value="${value//SERVER_IP/$SERVER_IP}"
  if grep -q "^${key}=" "$PROJECT_DIR/.env"; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$PROJECT_DIR/.env"
  else
    echo "${key}=${value}" >> "$PROJECT_DIR/.env"
  fi
done

chmod +x "$PROJECT_DIR/start.sh"
mkdir -p "$PROJECT_DIR/backups"

read -rp "  Собрать Docker-образы сейчас? [Y/n]: " BUILD_NOW
if [[ "${BUILD_NOW:-Y}" =~ ^[Yy]$ ]]; then
  cd "$PROJECT_DIR"; DOCKER_BUILDKIT=1 docker compose build && success "Образы собраны"
  docker compose up -d --no-build && success "Стек запущен" || warn "Запусти: bash start.sh → 4) Пересборка"
fi

echo; echo -e "${GREEN}${BOLD}  Установка завершена!${NC}"
echo -e "  Домен: https://${DOMAIN}   IP: ${SERVER_IP}"
echo -e "  Дальше: cd $PROJECT_DIR && bash start.sh → 1) Запуск"
