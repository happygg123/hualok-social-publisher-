from __future__ import annotations

import uvicorn

HOST = "127.0.0.1"
PORT = 8765


def main() -> int:
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
