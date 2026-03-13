import uvicorn

import src.server as server


def main():
    print("[main] Starting liturgy display app...")

    print("[main] Starting server on http://0.0.0.0:8000")
    uvicorn.run(server.app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
