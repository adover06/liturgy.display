import asyncio
import json
import logging
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse


app = FastAPI()
logger = logging.getLogger("display.server")

clients = set()
broadcast_queue = asyncio.Queue()

# Store the event loop reference for cross-thread access
_loop = None


@app.get("/", response_class=HTMLResponse)
async def index():
    return Path("static/index.html").read_text(encoding="utf-8")


@app.get("/control", response_class=HTMLResponse)
async def control():
    return Path("static/control.html").read_text(encoding="utf-8")


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    import src.voice_rec as voice_rec

    await ws.accept()
    clients.add(ws)
    logger.info("WebSocket client connected total=%s", len(clients))
    try:
        while True:
            raw = await ws.receive_text()
            logger.debug("WebSocket command received payload=%s", raw)
            m = json.loads(raw)

            await voice_rec.handle_command(
                m.get("cmd", ""),
                m.get("title", ""),
                m.get("text", ""),
            )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.exception("WebSocket command channel error: %s", e)
    finally:
        clients.discard(ws)
        logger.info("WebSocket client disconnected total=%s", len(clients))


@app.websocket("/ws/audio")
async def ws_audio_endpoint(ws: WebSocket):
    import src.voice_rec as voice_rec

    await ws.accept()
    logger.debug("Audio stream client connected")
    voice_rec.start_audio_session()
    chunk_count = 0
    total_bytes = 0
    try:
        while True:
            data = await ws.receive_bytes()
            chunk_count += 1
            total_bytes += len(data)
            if chunk_count % 100 == 0:
                logger.debug(
                    "Audio stream stats chunks=%s bytes=%s avg_chunk=%s",
                    chunk_count,
                    total_bytes,
                    total_bytes // chunk_count,
                )
            voice_rec.ingest_audio_chunk(data)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.exception("Audio websocket error: %s", e)
    finally:
        logger.debug(
            "Audio stream summary chunks=%s bytes=%s", chunk_count, total_bytes
        )
        voice_rec.stop_audio_session()
        logger.debug("Audio stream client disconnected")


async def _broadcaster():
    """Background task that sends queued messages to all connected displays"""
    while True:
        msg = await broadcast_queue.get()
        logger.debug("Broadcasting payload=%s", msg)
        dead = []
        for c in list(clients):
            try:
                await c.send_text(msg)
            except Exception:
                dead.append(c)
        for c in dead:
            clients.discard(c)


def send_command(command: dict):
    """Thread-safe way to send commands to all display clients"""
    if _loop is None:
        logger.warning("Event loop not ready yet; dropping command=%s", command)
        return
    _loop.call_soon_threadsafe(broadcast_queue.put_nowait, json.dumps(command))


@app.on_event("startup")
async def startup_event():
    global _loop
    _loop = asyncio.get_running_loop()  # Store the running loop
    asyncio.create_task(_broadcaster())
    logger.info("Background broadcaster scheduled")
