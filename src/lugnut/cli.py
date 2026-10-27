import argparse

import uvicorn

from lugnut.settings import Settings


def main() -> None:
    settings = Settings()
    parser = argparse.ArgumentParser(prog="lugnut")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="run the web server")
    serve.add_argument("--host", default=settings.host)
    serve.add_argument("--port", type=int, default=settings.port)
    args = parser.parse_args()
    uvicorn.run("lugnut.app:create_app", factory=True, host=args.host, port=args.port)
