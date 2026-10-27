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

The maintainer cuts releases. Merged PR titles become the release notes, so write them for the people using Lugnut.

## Workflows

Workflows refer to actions by tag, and `.github/workflows/actions.lock` pins each tag to a commit. GitHub will not run a workflow whose actions are missing from the lockfile. After adding or changing an action, run `gh actions-lock` and commit the updated lockfile. Check it with `gh actions-lock --no-fix`.
