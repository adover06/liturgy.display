import logging

import uvicorn

import src.server as server


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logger = logging.getLogger("display.main")

    logger.info("Starting liturgy display app")
    logger.info("Starting server on http://0.0.0.0:8000")
    uvicorn.run(server.app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
