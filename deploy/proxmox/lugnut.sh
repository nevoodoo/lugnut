#!/usr/bin/env bash
# Creates a Lugnut LXC container on a Proxmox VE host, or updates one.
# Run as root on the Proxmox host.
#
#   bash lugnut.sh                 create a container (asks for each setting)
#   bash lugnut.sh -y              create a container with defaults, no prompts
#   bash lugnut.sh update <ctid>   update Lugnut inside an existing container
#
# Every prompt can be preset with an environment variable:
#   LUGNUT_CTID, LUGNUT_HOSTNAME, LUGNUT_TEMPLATE_STORAGE, LUGNUT_STORAGE,
#   LUGNUT_BRIDGE, LUGNUT_IP, LUGNUT_GATEWAY, LUGNUT_CORES, LUGNUT_RAM, LUGNUT_DISK
# Other variables:
#   LUGNUT_YES=1          same as -y
#   LUGNUT_VERSION        pin a release, for example 0.1.0rc1 (default: latest stable)
#   LUGNUT_SOURCE         wheel URL, or a wheel path on this host
#   LUGNUT_INSTALL_URL    where to fetch lugnut-install.sh when it is not next to this script
set -euo pipefail

DEFAULT_INSTALL_URL=https://raw.githubusercontent.com/nevoodoo/lugnut/main/deploy/proxmox/lugnut-install.sh
PORT=8080
ASSUME_YES="${LUGNUT_YES:-0}"
WORKDIR=""

log() { printf '==> %s\n' "$*" >&2; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

cleanup() {
  if [[ -n "$WORKDIR" ]]; then
    rm -rf "$WORKDIR"
  fi
}
trap cleanup EXIT

check_host() {
  [[ "$EUID" -eq 0 ]] || die "run this as root on the Proxmox host"
  local tool
  for tool in pct pvesh pvesm pveam; do
    command -v "$tool" >/dev/null 2>&1 || die "$tool not found, this must run on a Proxmox VE host"
  done
}

# ask <value-from-env> <prompt> <default>: prints the value to use.
ask() {
  local preset="$1" prompt="$2" default="$3" reply=""
  if [[ -n "$preset" ]]; then
    printf '%s\n' "$preset"
    return
  fi
  if [[ "$ASSUME_YES" != 1 ]]; then
    read -r -p "$prompt [$default]: " reply || reply=""
  fi
  printf '%s\n' "${reply:-$default}"
}

# Storage names that can hold the given content type (vztmpl or rootdir).
list_storages() {
  # pvesm probes every storage; a broken or inactive one prints errors we do not need.
  pvesm status --content "$1" 2>/dev/null | awk 'NR > 1 { print $1 }'
}

show_storages() {
  printf 'Storages for %s: %s\n' "$1" "$(list_storages "$1" | tr '\n' ' ')" >&2
}

next_ctid() {
  pvesh get /cluster/nextid | tr -d '"[:space:]'
}

latest_template() {
  pveam available --section system | awk '$2 ~ /^debian-13-standard/ { print $2 }' | sort -V | tail -n 1
}

ensure_template() {
  local storage="$1" template
  log "Looking for the latest Debian 13 template"
  pveam update >/dev/null
  template="$(latest_template)"
  [[ -n "$template" ]] || die "no debian-13-standard template found in 'pveam available'"
  if pveam list "$storage" | awk '{ print $1 }' | grep -qF "$storage:vztmpl/$template"; then
    log "Template $template is already on $storage"
  else
    log "Downloading $template to $storage"
    pveam download "$storage" "$template" >&2
  fi
  printf '%s\n' "$template"
}

# Prints the install script path: the copy next to this script, or a download.
find_install_script() {
  local source_file="${BASH_SOURCE[0]:-}" here
  if [[ -n "$source_file" && -f "$source_file" ]]; then
    here="$(cd "$(dirname "$source_file")" && pwd)"
    if [[ -f "$here/lugnut-install.sh" ]]; then
      printf '%s\n' "$here/lugnut-install.sh"
      return
    fi
  fi
  WORKDIR="$(mktemp -d)"
  log "Downloading lugnut-install.sh"
  curl -fsSL "${LUGNUT_INSTALL_URL:-$DEFAULT_INSTALL_URL}" -o "$WORKDIR/lugnut-install.sh"
  printf '%s\n' "$WORKDIR/lugnut-install.sh"
}

wait_for_network() {
  local ctid="$1"
  log "Waiting for the container network"
  for _ in $(seq 1 60); do
    if pct exec "$ctid" -- getent hosts deb.debian.org >/dev/null 2>&1; then
      return
    fi
    sleep 2
  done
  die "container $ctid has no network after 2 minutes; check the bridge, IP and gateway"
}

container_ip() {
  pct exec "$1" -- hostname -I | awk '{ print $1 }'
}

# push_source <ctid>: if LUGNUT_SOURCE is a file on this host, copies it into the
# container. Prints the value to hand to the in-container script (empty if unset).
push_source() {
  local ctid="$1" source="${LUGNUT_SOURCE:-}"
  if [[ -n "$source" && -f "$source" ]]; then
    pct push "$ctid" "$source" "/tmp/$(basename "$source")" >&2
    printf '/tmp/%s\n' "$(basename "$source")"
  else
    printf '%s\n' "$source"
  fi
}

run_in_container() {
  local ctid="$1" script="$2" source
  source="$(push_source "$ctid")"
  pct exec "$ctid" -- env "LUGNUT_VERSION=${LUGNUT_VERSION:-}" "LUGNUT_SOURCE=$source" "$script"
}

create_container() {
  local ctid="$1" hostname="$2" tstorage="$3" template="$4" rstorage="$5"
  local disk="$6" cores="$7" ram="$8" net="$9"
  log "Creating container $ctid"
  pct create "$ctid" "$tstorage:vztmpl/$template" \
    --hostname "$hostname" \
    --ostype debian \
    --unprivileged 1 \
    --features nesting=1 \
    --onboot 1 \
    --cores "$cores" \
    --memory "$ram" \
    --rootfs "$rstorage:$disk" \
    --net0 "$net"
}

install() {
  local ctid hostname tstorage rstorage bridge ip gateway cores ram disk net template script ip_addr
  ctid="$(ask "${LUGNUT_CTID:-}" "Container ID" "$(next_ctid)")"
  hostname="$(ask "${LUGNUT_HOSTNAME:-}" "Hostname" lugnut)"
  [[ -z "${LUGNUT_TEMPLATE_STORAGE:-}" && "$ASSUME_YES" != 1 ]] && show_storages vztmpl
  tstorage="$(ask "${LUGNUT_TEMPLATE_STORAGE:-}" "Template storage" local)"
  [[ -z "${LUGNUT_STORAGE:-}" && "$ASSUME_YES" != 1 ]] && show_storages rootdir
  rstorage="$(ask "${LUGNUT_STORAGE:-}" "Container storage" local-lvm)"
  bridge="$(ask "${LUGNUT_BRIDGE:-}" "Network bridge" vmbr0)"
  ip="$(ask "${LUGNUT_IP:-}" "IP address (dhcp, or CIDR like 192.168.1.50/24)" dhcp)"
  net="name=eth0,bridge=$bridge,ip=$ip"
  if [[ "$ip" != dhcp ]]; then
    gateway="$(ask "${LUGNUT_GATEWAY:-}" "Gateway" "")"
    [[ -n "$gateway" ]] || die "a static IP needs a gateway (LUGNUT_GATEWAY)"
    net="$net,gw=$gateway"
  fi
  cores="$(ask "${LUGNUT_CORES:-}" "CPU cores" 1)"
  ram="$(ask "${LUGNUT_RAM:-}" "RAM in MB" 512)"
  disk="$(ask "${LUGNUT_DISK:-}" "Disk in GB" 4)"

  [[ "$ctid" =~ ^[0-9]+$ ]] || die "container ID must be a number"
  if pct status "$ctid" >/dev/null 2>&1; then
    die "container $ctid already exists"
  fi

  if [[ "$ASSUME_YES" != 1 ]]; then
    printf '\nAbout to create container %s (%s): %s cores, %s MB RAM, %s GB disk on %s, network %s.\n' \
      "$ctid" "$hostname" "$cores" "$ram" "$disk" "$rstorage" "$ip" >&2
    local ok
    read -r -p "Continue? [Y/n]: " ok || ok=""
    [[ -z "$ok" || "$ok" =~ ^[Yy] ]] || die "cancelled"
  fi

  script="$(find_install_script)"
  template="$(ensure_template "$tstorage")"
  create_container "$ctid" "$hostname" "$tstorage" "$template" "$rstorage" "$disk" "$cores" "$ram" "$net"
  log "Starting container $ctid"
  pct start "$ctid"
  wait_for_network "$ctid"

  log "Installing Lugnut"
  pct push "$ctid" "$script" /tmp/lugnut-install.sh --perms 0755
  run_in_container "$ctid" /tmp/lugnut-install.sh
  pct exec "$ctid" -- rm -f /tmp/lugnut-install.sh

  ip_addr="$(container_ip "$ctid")"
  log "Lugnut is ready: http://$ip_addr:$PORT"
  echo "Open it to create your account. To update later, run on this host: pct exec $ctid -- lugnut-update"
}

update() {
  local ctid="${1:-}"
  [[ "$ctid" =~ ^[0-9]+$ ]] || die "usage: lugnut.sh update <ctid>"
  pct status "$ctid" 2>/dev/null | grep -q running || die "container $ctid is not running"
  run_in_container "$ctid" /usr/local/bin/lugnut-update
}

usage() {
  sed -n '2,/^set -euo/p' "${BASH_SOURCE[0]}" | sed '$d' | sed 's/^# \{0,1\}//'
}

main() {
  local command=install
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -y|--yes) ASSUME_YES=1 ;;
      -h|--help) usage; exit 0 ;;
      install) command=install ;;
      update) command=update; shift; break ;;
      *) die "unknown argument: $1 (try --help)" ;;
    esac
    shift
  done
  check_host
  if [[ "$command" == update ]]; then
    update "$@"
  else
    install
  fi
}

main "$@"
