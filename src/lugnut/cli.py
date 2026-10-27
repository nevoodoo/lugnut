import argparse

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(prog="lugnut")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="run the web server")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run("lugnut.app:create_app", factory=True, host=args.host, port=args.port)
