# Install with Docker

The image is `ghcr.io/nevoodoo/lugnut`. It listens on port 8080 and keeps all its data in `/data`.

```sh
docker run -d --name lugnut \
  -p 8080:8080 \
  -v lugnut-data:/data \
  -e LUGNUT_SECURE_COOKIES=false \
  ghcr.io/nevoodoo/lugnut:latest
```

Then open `http://localhost:8080` and create your account.

Release candidates are tagged `rc` and are not moved to `latest`. Pin a version tag such as `0.1.0` if you want upgrades to happen only when you choose.

## Plain HTTP and the session cookie

The login cookie is marked Secure by default, so browsers only send it over HTTPS. If you reach Lugnut over plain HTTP, which is common on a home network, set `LUGNUT_SECURE_COOKIES=false` as in the example above. Otherwise login will appear to work and then not stick.

If you put Lugnut behind a reverse proxy that serves HTTPS, leave the setting at its default.

## Compose

```yaml
services:
  lugnut:
    image: ghcr.io/nevoodoo/lugnut:latest
    ports:
      - "8080:8080"
    volumes:
      - lugnut-data:/data
    environment:
      LUGNUT_SECURE_COOKIES: "false" # remove if you serve HTTPS
    restart: unless-stopped

volumes:
  lugnut-data:
```

## Your data

Everything lives in the `/data` volume:

| Path | Contents |
| --- | --- |
| `lugnut.db` | The database |
| `backups/` | Automatic copies of the database, made before each migration |
| `attachments/` | Uploaded files |

The container runs as user 1000. If you use a bind mount instead of a named volume, make the directory writable by that user.

## Upgrading

Pull the new image and recreate the container. The database is migrated on startup, after a backup is copied into `backups/`. Migrations only go forward, so keep your own backup too before upgrading across versions.

## Settings

| Variable | Default | Meaning |
| --- | --- | --- |
| `LUGNUT_DATA_DIR` | `/data` in the image | Where the data lives |
| `LUGNUT_HOST` | `0.0.0.0` in the image | Address to listen on |
| `LUGNUT_PORT` | `8080` | Port to listen on |
| `LUGNUT_SECURE_COOKIES` | `true` | Set to `false` when serving plain HTTP |

How you reach Lugnut from outside your network (VPN, reverse proxy) is up to you.
