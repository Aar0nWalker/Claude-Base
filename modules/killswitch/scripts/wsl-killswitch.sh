#!/bin/bash
# {{PROJECT_NAME}} killswitch — WSL ({{WSL_DISTRO}}) part. Run as root inside WSL.
#
# Blocks all direct outbound internet from the {{WSL_DISTRO}} distro; traffic must go
# through Clash on the Windows host (private ranges stay open, so agents in WSL
# reach clash(172.17.x.x:{{CLASH_PORT}}) as usual).
# The prod server stays reachable directly (deploy/ssh/rsync).
#
# Docker Desktop containers live in the separate docker-desktop distro and are
# NOT affected by these rules.
#
# usage: wsl-killswitch.sh on|off|status|apply
#   on     - apply rules now + install systemd unit so they survive WSL restart
#   off    - remove rules + uninstall systemd unit
#   status - show current state
#   apply  - apply rules only (used by the systemd unit at boot)
set -u

CHAIN={{PROJECT_SLUG}}_KILLSWITCH
# Direct-access exceptions (bypass proxy). Edit here, then re-run "on".
ALLOW_IPS=(
  "{{PROD_IP}}"   # prod server (deploy.sh / ssh / rsync)
)
UNIT=/etc/systemd/system/{{PROJECT_SLUG}}-killswitch.service
SELF_INSTALLED=/usr/local/sbin/{{PROJECT_SLUG}}-killswitch
IPT=/usr/sbin/iptables

[ "$(id -u)" = "0" ] || { echo "run as root (wsl -u root)"; exit 1; }

ensure_iptables() {
  [ -x "$IPT" ] && return 0
  echo "iptables not found, installing..."
  apt-get update -qq && apt-get install -y -qq iptables
}

apply() {
  ensure_iptables || { echo "FAIL: cannot install iptables"; exit 1; }
  $IPT -N $CHAIN 2>/dev/null || $IPT -F $CHAIN
  $IPT -A $CHAIN -o lo -j ACCEPT
  $IPT -A $CHAIN -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
  # Windows host (Clash, DNS) + any local nets
  for net in 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16 169.254.0.0/16; do
    $IPT -A $CHAIN -d "$net" -j ACCEPT
  done
  for ip in "${ALLOW_IPS[@]}"; do
    $IPT -A $CHAIN -d "$ip" -j ACCEPT
  done
  # Reject (not drop) so apps fail fast instead of hanging on timeouts.
  $IPT -A $CHAIN -p tcp -j REJECT --reject-with tcp-reset
  $IPT -A $CHAIN -j REJECT
  $IPT -C OUTPUT -j $CHAIN 2>/dev/null || $IPT -I OUTPUT 1 -j $CHAIN
}

enable_persist() {
  cp "$(readlink -f "$0")" "$SELF_INSTALLED" && chmod +x "$SELF_INSTALLED"
  cat > "$UNIT" <<EOF
[Unit]
Description={{PROJECT_NAME}} network killswitch (WSL outbound via Clash only)
After=network.target

[Service]
Type=oneshot
ExecStart=$SELF_INSTALLED apply
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable {{PROJECT_SLUG}}-killswitch.service >/dev/null 2>&1
}

remove() {
  if [ -x "$IPT" ]; then
    $IPT -D OUTPUT -j $CHAIN 2>/dev/null
    $IPT -F $CHAIN 2>/dev/null
    $IPT -X $CHAIN 2>/dev/null
  fi
  systemctl disable {{PROJECT_SLUG}}-killswitch.service >/dev/null 2>&1
  rm -f "$UNIT" "$SELF_INSTALLED"
  systemctl daemon-reload
}

status() {
  if [ -x "$IPT" ] && $IPT -C OUTPUT -j $CHAIN 2>/dev/null; then
    echo "WSL killswitch: ON"
    $IPT -L $CHAIN -n --line-numbers
  else
    echo "WSL killswitch: OFF"
  fi
}

case "${1:-}" in
  on)     apply && enable_persist && status ;;
  apply)  apply ;;
  off)    remove; echo "WSL killswitch: OFF" ;;
  status) status ;;
  *)      echo "usage: $0 on|off|status"; exit 1 ;;
esac
