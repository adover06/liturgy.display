import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse


app = FastAPI()

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
    print(f"[server] Client connected. Total clients: {len(clients)}")
    try:
        while True:
            raw = await ws.receive_text()
            print(f"[server] Received: {raw}")
            m = json.loads(raw)

            await voice_rec.handle_command(
                m.get("cmd", ""),
                m.get("title", ""),
                m.get("text", ""),
            )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[server] WebSocket error: {e}")
    finally:
        clients.discard(ws)
        print(f"[server] Client disconnected. Total clients: {len(clients)}")


@app.websocket("/ws/audio")
async def ws_audio_endpoint(ws: WebSocket):
    import src.voice_rec as voice_rec

    await ws.accept()
    print("[server] Audio client connected")
    voice_rec.start_audio_session()
    try:
        while True:
            data = await ws.receive_bytes()
            voice_rec.ingest_audio_chunk(data)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[server] Audio WebSocket error: {e}")
    finally:
        voice_rec.stop_audio_session()
        print("[server] Audio client disconnected")


async def _broadcaster():
    """Background task that sends queued messages to all connected displays"""
    while True:
        msg = await broadcast_queue.get()
        print(f"[server] Broadcasting: {msg}")
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
        print("[server] WARNING: Event loop not ready yet")
        return
    _loop.call_soon_threadsafe(broadcast_queue.put_nowait, json.dumps(command))


@app.on_event("startup")
async def startup_event():
    global _loop
    _loop = asyncio.get_running_loop()  # Store the running loop
    asyncio.create_task(_broadcaster())
    print("Background task scheduled on startup.")
