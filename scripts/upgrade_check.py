"""Upgrade check: data written by the newest PyPI release must work with this build.

Usage: python scripts/upgrade_check.py path/to/current.whl
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

PLACEHOLDER = "0.0.1"
PORT = 18080
BASE = f"http://127.0.0.1:{PORT}"
CREDS = {"username": "upgrade", "password": "correct horse battery staple"}


def newest_release() -> str | None:
    with urllib.request.urlopen("https://pypi.org/pypi/lugnut/json", timeout=30) as r:
        releases = json.load(r)["releases"]
    final = [
        v
        for v, files in releases.items()
        if files and re.fullmatch(r"\d+(\.\d+)*", v) and v != PLACEHOLDER
    ]
    # ponytail: numeric sort of plain x.y.z versions, enough until odd version schemes appear
    final.sort(key=lambda v: tuple(map(int, v.split("."))))
    return final[-1] if final else None


def post(path: str, body: dict[str, str], expect: int) -> None:
    req = urllib.request.Request(
        BASE + path, json.dumps(body).encode(), {"Content-Type": "application/json"}
    )
    try:
        status = urllib.request.urlopen(req, timeout=10).status
    except urllib.error.HTTPError as e:
        status = e.code
    if status != expect:
        sys.exit(f"POST {path}: expected {expect}, got {status}")


def run_server(venv: Path, env: dict[str, str]) -> subprocess.Popen[bytes]:
    proc = subprocess.Popen([venv / "bin" / "lugnut", "serve", "--port", str(PORT)], env=env)
    for _ in range(30):
        try:
            urllib.request.urlopen(BASE + "/api/health", timeout=2)
            return proc
        except OSError:
            time.sleep(1)
    proc.kill()
    sys.exit("server did not start")


def stop(proc: subprocess.Popen[bytes]) -> None:
    proc.terminate()
    proc.wait(timeout=15)


def make_venv(tmp: Path, name: str, package: str) -> Path:
    venv = tmp / name
    subprocess.run(["uv", "venv", "--quiet", str(venv)], check=True)
    subprocess.run(
        ["uv", "pip", "install", "--quiet", "--python", str(venv / "bin" / "python"), package],
        check=True,
    )
    return venv


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: upgrade_check.py CURRENT_WHEEL")
    old = newest_release()
    if old is None:
        print("no previous release")
        return
    wheel = str(Path(sys.argv[1]).resolve())
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        env = {**os.environ, "LUGNUT_DATA_DIR": str(tmp / "data"), "LUGNUT_SECURE_COOKIES": "false"}
        proc = run_server(make_venv(tmp, "old", f"lugnut=={old}"), env)
        try:
            post("/api/setup", CREDS, 201)
        finally:
            stop(proc)
        proc = run_server(make_venv(tmp, "new", wheel), env)
        try:
            post("/api/auth/login", CREDS, 200)
        finally:
            stop(proc)
    print(f"upgrade from {old} ok")


if __name__ == "__main__":
    main()
