#!/usr/bin/env bash
# Installs or reinstalls Lugnut inside a Debian 13 container. Run as root.
# Safe to run more than once. Settings in /etc/lugnut.env are never overwritten.
#
# Environment:
#   LUGNUT_VERSION     pin a release, for example 0.1.0rc1 (default: latest stable)
#   LUGNUT_SOURCE      wheel URL or path to install instead of the PyPI release
#   LUGNUT_NO_SYSTEMD  set to 1 to skip systemd (for testing in Docker)
set -euo pipefail

APP_HOME=/opt/lugnut
ENV_FILE=/etc/lugnut.env
VERSION="${LUGNUT_VERSION:-}"
SOURCE="${LUGNUT_SOURCE:-}"
NO_SYSTEMD="${LUGNUT_NO_SYSTEMD:-0}"

log() { printf '==> %s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

install_packages() {
  log "Installing curl and ca-certificates"
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq curl ca-certificates
}

install_uv() {
  if [[ -x /usr/local/bin/uv ]]; then
    log "uv is already installed"
    return
  fi
  log "Installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin UV_NO_MODIFY_PATH=1 sh
}

create_user() {
  if id lugnut >/dev/null 2>&1; then
    return
  fi
  log "Creating system user lugnut"
  useradd --system --home-dir "$APP_HOME" --create-home --shell /usr/sbin/nologin lugnut
}

# The package spec uv should install: a wheel, a pinned version, or the latest release.
package_spec() {
  if [[ -n "$SOURCE" ]]; then
    printf '%s\n' "$SOURCE"
  elif [[ -n "$VERSION" ]]; then
    printf 'lugnut==%s\n' "$VERSION"
  else
    printf 'lugnut\n'
  fi
}

install_lugnut() {
  local spec
  spec="$(package_spec)"
  log "Installing $spec"
  mkdir -p "$APP_HOME/data"
  # Python lives under /opt/lugnut so the service user can read it (root's home is private).
  UV_TOOL_DIR="$APP_HOME/tools" UV_TOOL_BIN_DIR=/usr/local/bin \
    UV_PYTHON_INSTALL_DIR="$APP_HOME/python" \
    uv tool install --force --python 3.13 "$spec"
  chown lugnut:lugnut "$APP_HOME" "$APP_HOME/data"
}

write_env_file() {
  if [[ -e "$ENV_FILE" ]]; then
    log "Keeping existing $ENV_FILE"
    return
  fi
  log "Writing $ENV_FILE"
  cat >"$ENV_FILE" <<'ENVEOF'
# Lugnut settings. Restart after editing: systemctl restart lugnut
LUGNUT_DATA_DIR=/opt/lugnut/data
LUGNUT_HOST=0.0.0.0
LUGNUT_PORT=8080
# The session cookie is Secure by default, and browsers drop it over plain HTTP
# on a LAN address, which breaks login. Set this to true if you put Lugnut
# behind an HTTPS reverse proxy.
LUGNUT_SECURE_COOKIES=false
ENVEOF
}

write_unit() {
  cat >/etc/systemd/system/lugnut.service <<'UNITEOF'
[Unit]
Description=Lugnut vehicle maintenance tracker
After=network-online.target
Wants=network-online.target

[Service]
User=lugnut
Group=lugnut
EnvironmentFile=/etc/lugnut.env
ExecStart=/usr/local/bin/lugnut serve
Restart=on-failure
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/opt/lugnut
PrivateTmp=true

[Install]
WantedBy=multi-user.target
UNITEOF
}

write_update_script() {
  cat >/usr/local/bin/lugnut-update <<'UPDEOF'
#!/usr/bin/env bash
# Updates Lugnut. With LUGNUT_VERSION or LUGNUT_SOURCE set, reinstalls that
# version or wheel instead of upgrading to the latest release.
set -euo pipefail

export UV_TOOL_DIR=/opt/lugnut/tools
export UV_TOOL_BIN_DIR=/usr/local/bin
export UV_PYTHON_INSTALL_DIR=/opt/lugnut/python

if [[ -n "${LUGNUT_SOURCE:-}" ]]; then
  uv tool install --force --python 3.13 "$LUGNUT_SOURCE"
elif [[ -n "${LUGNUT_VERSION:-}" ]]; then
  uv tool install --force --python 3.13 "lugnut==$LUGNUT_VERSION"
else
  uv tool upgrade lugnut
fi

port=8080
if [[ -r /etc/lugnut.env ]]; then
  port="$(sed -n 's/^LUGNUT_PORT=//p' /etc/lugnut.env | tail -n 1)"
  port="${port:-8080}"
fi

if [[ "${LUGNUT_NO_SYSTEMD:-0}" == 1 ]]; then
  echo "LUGNUT_NO_SYSTEMD=1: restart lugnut yourself."
else
  systemctl restart lugnut
fi

for _ in $(seq 1 30); do
  if health="$(curl -fsS "http://127.0.0.1:$port/api/health" 2>/dev/null)"; then
    echo "Lugnut is running: $health"
    exit 0
  fi
  [[ "${LUGNUT_NO_SYSTEMD:-0}" == 1 ]] && break
  sleep 1
done
if [[ "${LUGNUT_NO_SYSTEMD:-0}" == 1 ]]; then
  echo "Not running (systemd skipped). Installed: $(uv tool list | head -n 1)"
  exit 0
fi
echo "Lugnut did not answer on port $port. Check: journalctl -u lugnut" >&2
exit 1
UPDEOF
  chmod 0755 /usr/local/bin/lugnut-update
}

start_service() {
  if [[ "$NO_SYSTEMD" == 1 ]]; then
    log "LUGNUT_NO_SYSTEMD=1, skipping systemd. Start it with:"
    echo "  setpriv --reuid=lugnut --regid=lugnut --clear-groups env \$(grep -v '^#' $ENV_FILE | xargs) /usr/local/bin/lugnut serve"
    return
  fi
  write_unit
  systemctl daemon-reload
  systemctl enable lugnut
  systemctl restart lugnut
}

main() {
  [[ "$EUID" -eq 0 ]] || die "run this as root"
  install_packages
  install_uv
  create_user
  install_lugnut
  write_env_file
  write_update_script
  start_service
  log "Done. Update later with: lugnut-update"
}

main
