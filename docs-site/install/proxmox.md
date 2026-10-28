# Install on Proxmox

A script on the Proxmox VE host creates an unprivileged LXC container with Debian 13, installs Lugnut in it and starts it as a systemd service. Run it as root in the host shell:

```sh
bash -c "$(curl -fsSL https://raw.githubusercontent.com/nevoodoo/lugnut/main/deploy/proxmox/lugnut.sh)"
```

It asks for each setting and shows a default in brackets. Press Enter to accept it. When it finishes it prints the address, for example `http://<container IP>:8080`. Open it and create your account.

There's no stable release yet. Until there is, pin a release candidate with `LUGNUT_VERSION` (see below).

## Options

Every prompt can be set ahead of time with an environment variable. Add `-y` (or `LUGNUT_YES=1`) to accept the defaults without any prompts:

```sh
LUGNUT_CTID=120 LUGNUT_DISK=8 LUGNUT_VERSION=0.1.0rc1 \
  bash -c "$(curl -fsSL https://raw.githubusercontent.com/nevoodoo/lugnut/main/deploy/proxmox/lugnut.sh)" -- -y
```

| Variable | Default | Meaning |
| --- | --- | --- |
| `LUGNUT_CTID` | next free ID | Container ID |
| `LUGNUT_HOSTNAME` | `lugnut` | Container hostname |
| `LUGNUT_TEMPLATE_STORAGE` | `local` | Storage that holds the Debian template |
| `LUGNUT_STORAGE` | `local-lvm` | Storage for the container disk |
| `LUGNUT_BRIDGE` | `vmbr0` | Network bridge |
| `LUGNUT_IP` | `dhcp` | `dhcp`, or an address like `192.168.1.50/24` |
| `LUGNUT_GATEWAY` | none | Gateway, required with a static address |
| `LUGNUT_CORES` | `1` | CPU cores |
| `LUGNUT_RAM` | `512` | Memory in MB |
| `LUGNUT_DISK` | `4` | Disk size in GB |
| `LUGNUT_PORT` | `8080` | Port Lugnut listens on. Use `80` to open it without a port number |
| `LUGNUT_YES` | `0` | Set to `1` to skip all prompts |
| `LUGNUT_VERSION` | latest stable | Install this version, for example `0.1.0rc1` |
| `LUGNUT_SOURCE` | none | A wheel URL, or a wheel path on the Proxmox host, to install instead of a release |

The script downloads the newest Debian 13 standard template if it isn't on the template storage yet. The container is unprivileged, has `nesting=1` and starts on boot.

## Updating

Run this on the Proxmox host:

```sh
bash -c "$(curl -fsSL https://raw.githubusercontent.com/nevoodoo/lugnut/main/deploy/proxmox/lugnut.sh)" -- update 120
```

Replace `120` with your container ID. It runs `lugnut-update` inside the container, which upgrades the package, restarts the service and prints the running version. You can also run `lugnut-update` yourself from a shell in the container. To run it straight from the host, give the full path, since `pct exec` doesn't include `/usr/local/bin` in its search path:

```sh
pct exec 120 -- env LUGNUT_VERSION=0.1.0rc2 /usr/local/bin/lugnut-update
```

To move to a specific version or wheel, set `LUGNUT_VERSION` or `LUGNUT_SOURCE` on the same command. An installation pinned to a version stays on it with a plain update.

## Where things live

| Path in the container | What it is |
| --- | --- |
| `/opt/lugnut/data` | Database (`lugnut.db`), `backups/` and `attachments/` |
| `/etc/lugnut.env` | Settings. The installer never overwrites it |
| `/etc/systemd/system/lugnut.service` | The service, which runs as the `lugnut` user |
| `/opt/lugnut/tools`, `/opt/lugnut/python` | The installed package and its Python |

`/etc/lugnut.env` sets `LUGNUT_SECURE_COOKIES=false` because the container serves plain HTTP on your LAN, and browsers drop a Secure cookie there. Change it to `true` if you put an HTTPS reverse proxy in front. After editing, run `systemctl restart lugnut`. The other variables are listed on the [local install page](local.md#settings).

Check the service with `systemctl status lugnut` and read logs with `journalctl -u lugnut`.

## Backups

Lugnut copies the database into `backups/` before it runs a migration. For a full backup, copy `/opt/lugnut/data`, or back up the whole container with Proxmox's own backup tools.

## Uninstall

Stop and destroy the container from the host. This deletes its data:

```sh
pct stop 120
pct destroy 120
```

## Changing the port

To move an existing install to another port, such as 80, edit `LUGNUT_PORT` in `/etc/lugnut.env` inside the container, then run `systemctl restart lugnut`. The service is allowed to use ports below 1024 without running as root.
