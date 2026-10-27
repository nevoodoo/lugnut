# Lugnut

> **Lugnut is in active development. Use it with caution and keep your own backups.** Right now it only has first-run setup, login and an empty home screen.

A self-hosted vehicle maintenance and running-cost tracker. One process, SQLite, no other services.

## Quick start

Docker:

```sh
docker run -d --name lugnut -p 8080:8080 -v lugnut-data:/data \
  -e LUGNUT_SECURE_COOKIES=false \
  ghcr.io/nevoodoo/lugnut:rc
```

Or with uv:

```sh
LUGNUT_SECURE_COOKIES=false uvx --prerelease=allow lugnut serve
```

Only release candidates exist so far. The `latest` image tag appears after the first stable release, and until then `uvx` needs `--prerelease=allow` (with pip, use `pip install --pre lugnut`); drop the flag once a stable release exists.

Then open http://localhost:8080. The examples turn off the Secure flag on the session cookie because plain HTTP would otherwise break login. Leave that variable out if you serve HTTPS. See the [install docs](https://nevoodoo.github.io/lugnut/install/docker/) for details.

## Docs

https://nevoodoo.github.io/lugnut, including the [roadmap](https://nevoodoo.github.io/lugnut/roadmap/).

## Coming from LubeLogger?

Importing a LubeLogger instance (backup zip or API) is planned and not available yet. Details are on the [docs page](https://nevoodoo.github.io/lugnut/coming-from-lubelogger/).

## Contributing

Pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

[MIT](LICENSE)
