# Install locally

You need [uv](https://docs.astral.sh/uv/) and Python 3.13 or newer (uv can fetch Python for you).

```sh
uvx lugnut serve
```

Then open `http://127.0.0.1:8080` and create your account. You can also `pip install lugnut` and run `lugnut serve`.

## Plain HTTP and the session cookie

The login cookie is marked Secure by default. Browsers do accept it on `localhost`, but not on other addresses served over plain HTTP, such as a LAN IP. If you serve Lugnut that way, start it with `LUGNUT_SECURE_COOKIES=false`:

```sh
LUGNUT_SECURE_COOKIES=false LUGNUT_HOST=0.0.0.0 uvx lugnut serve
```

## Settings

| Variable | Default | Meaning |
| --- | --- | --- |
| `LUGNUT_DATA_DIR` | `./data` | Where the data lives |
| `LUGNUT_HOST` | `127.0.0.1` | Address to listen on |
| `LUGNUT_PORT` | `8080` | Port to listen on |
| `LUGNUT_SECURE_COOKIES` | `true` | Set to `false` when serving plain HTTP |

The data directory holds `lugnut.db`, `backups/` (automatic copies made before each migration) and `attachments/`. Back it up as a whole.

## Upgrading

Run a newer version of the package. The database is migrated on startup, after a backup is copied into `backups/`.
