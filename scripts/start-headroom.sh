#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$ROOT/.headroom/proxy.pid"
LOG_FILE="$ROOT/.headroom/proxy.log"

# Local Clash / Clash Verge Rev proxy.
# In WSL 127.0.0.1 is not the Windows host, so auto-detect the host IP from
# resolv.conf. Override with CLASH_PROXY_URL env if needed.
if [[ -z "${CLASH_PROXY_URL:-}" ]] && grep -qi microsoft /proc/version 2>/dev/null; then
  WIN_IP="$(awk '/^nameserver/ {print $2; exit}' /etc/resolv.conf 2>/dev/null)"
  [[ -n "$WIN_IP" ]] && CLASH_PROXY_URL="http://$WIN_IP:{{CLASH_PORT}}"
fi
CLASH_PROXY_URL="${CLASH_PROXY_URL:-http://127.0.0.1:{{CLASH_PORT}}}"

# Keep local/dev addresses direct. Important: Headroom livez and Codex->Headroom
# must stay local and must NOT go through Clash.
NO_PROXY_VALUE="${NO_PROXY_VALUE:-localhost,127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16}"

mkdir -p "$ROOT/.headroom"

emit() {
  if [[ -n "${PLUGIN_DATA:-}" ]]; then
    echo "$*" >&2
  else
    echo "$*"
  fi
}

emit_task_context() {
  [[ -n "${PLUGIN_DATA:-}" ]] || return 0
  CODEX_HOOK_EVENT="${CODEX_HOOK_EVENT:-SessionStart}" "$ROOT/scripts/agent-task-hook.sh" Codex || true
}

listener_pid() {
  ss -ltnp "sport = :8788" 2>/dev/null \
    | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' \
    | head -n 1
}

is_headroom_pid() {
  local pid="$1"
  [[ -n "$pid" ]] && tr '\0' ' ' <"/proc/$pid/cmdline" 2>/dev/null | grep -qi headroom
}

PID="$(listener_pid)"
if [[ -n "$PID" ]]; then
  if is_headroom_pid "$PID"; then
    echo "$PID" > "$PID_FILE"
    emit "Headroom already listening on 127.0.0.1:8788: pid $PID"
    emit_task_context
    exit 0
  fi
  echo "Port 8788 is occupied by non-Headroom process: pid $PID" >&2
  exit 1
fi

if [[ -f "$PID_FILE" ]]; then
  PID="$(cat "$PID_FILE")"
  if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
    emit "Removing stale Headroom pid: $PID"
  fi
  rm -f "$PID_FILE"
fi

{
  echo "=== $(date -Is) start-headroom ==="
  echo "headroom binary: $ROOT/.venv-headroom/bin/headroom"
  echo "CLASH_PROXY_URL: $CLASH_PROXY_URL"
  echo "NOTE: this file only captures stdout/stderr; request logs are in ~/.headroom/logs/proxy.log"
} >>"$LOG_FILE"

(
  export HEADROOM_TELEMETRY=off
  export PATH="$ROOT/.tools/bin:$PATH"

  export HTTP_PROXY="$CLASH_PROXY_URL"
  export HTTPS_PROXY="$CLASH_PROXY_URL"
  export ALL_PROXY="$CLASH_PROXY_URL"

  export http_proxy="$CLASH_PROXY_URL"
  export https_proxy="$CLASH_PROXY_URL"
  export all_proxy="$CLASH_PROXY_URL"

  export NO_PROXY="$NO_PROXY_VALUE"
  export no_proxy="$NO_PROXY_VALUE"

  exec "$ROOT/.venv-headroom/bin/headroom" proxy \
    --host 127.0.0.1 \
    --port 8788 \
    --mode token \
    --backend anthropic \
    --no-telemetry \
    >>"$LOG_FILE" 2>&1
) </dev/null &

echo "$!" > "$PID_FILE"

for _ in {1..20}; do
  if curl --noproxy "*" -fsS -m 1 http://127.0.0.1:8788/livez >/dev/null 2>&1; then
    PID="$(listener_pid)"
    [[ -n "$PID" ]] && echo "$PID" > "$PID_FILE"
    emit "Started Headroom: pid $(cat "$PID_FILE")"
    emit "Headroom outbound proxy: $CLASH_PROXY_URL"
    emit "Request logs: ~/.headroom/logs/proxy.log (stdout log: $LOG_FILE)"
    emit_task_context
    exit 0
  fi
  sleep 0.25
done

echo "Headroom did not become ready. Last log lines:" >&2
tail -40 "$LOG_FILE" >&2 || true
exit 1