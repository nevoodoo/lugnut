# Contributing

Pull requests are welcome. Lugnut has one maintainer: anyone can open a PR, but only the maintainer merges and releases. For anything large, open an issue first so you don't build something that won't be merged.

## Setup

You need [uv](https://docs.astral.sh/uv/), Node 22 and npm.

```sh
git clone https://github.com/nevoodoo/lugnut
cd lugnut
uv sync
cd frontend && npm ci && cd ..
uv run pre-commit install
```

Run the backend with `uv run lugnut serve` (set `LUGNUT_SECURE_COOKIES=false` if you use plain HTTP) and the frontend with `npm run dev` in `frontend/`. The frontend proxies `/api` to port 8080. `npm run build` writes the built app into the Python package.

Before opening a PR, run `uv run ruff check`, `uv run ruff format --check`, `uv run mypy` and `uv run pytest`, then `npm run lint` and `npm run build` in `frontend/`. Pre-commit runs the Python checks on commit.

## Pull requests

Write the PR title as a conventional commit, in one plain sentence aimed at users, for example `feat: add insurance records` or `fix: keep the odometer when editing a fuel record`. PRs are squash merged, so the title becomes the changelog line.

Only finished features get merged, so `main` can always be released. Don't expose a half-built feature in the interface.

## Tests

Test behaviour that can realistically break: data loss, auth, migrations, and API contracts the frontend uses. Don't test framework behaviour, config files or trivial code. There is no coverage target.

## Releases

These notes are for the maintainer.

release-please opens a release PR from the conventional commit titles on `main`. Merging it creates a draft GitHub release and a tag. A `publish` job then waits for the maintainer's approval in the `release` environment and publishes to PyPI, to `ghcr.io/nevoodoo/lugnut` and to the GitHub release.

To cut a release candidate, push an empty commit to `main` before merging the release PR:

```sh
git commit --allow-empty -m "chore: release 0.1.0-rc.1" -m "Release-As: 0.1.0-rc.1"
```

The footer must be the last paragraph. The git tag is `v0.1.0-rc.1`, PyPI and the image use `0.1.0rc1`, the GitHub release is marked as a pre-release, and the image is also tagged `rc` (not `latest`). To publish the final release after a candidate, use `Release-As: 0.1.0` the same way.

Workflow actions are pinned by commit SHA and recorded in `.github/workflows/actions.lock`. Check them with `gh actions-lock --no-fix`. Running `gh actions-lock` without `--no-fix` rewrites SHA pins to tags, so restore the SHAs after refreshing the lock.
