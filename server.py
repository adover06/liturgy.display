import asyncio, json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from reading import fetch_daily_material_object
from pathlib import Path


app = FastAPI()

clients = set()
broadcast_queue = asyncio.Queue()

READINGS = {}

@app.get("/", response_class=HTMLResponse)
async def index():
    return Path("static/index.html").read_text(encoding="utf-8")

@app.get("/control", response_class=HTMLResponse)
async def control():
    return Path("static/control.html").read_text(encoding="utf-8")

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    try:
        while True:
            raw = await ws.receive_text()
            m = json.loads(raw)
            if m["cmd"] == "show":
                section = m.get("title")
                text = READINGS.get(section)
                output = {"cmd": "set", "title": "", "text": text}
                await broadcast_queue.put(json.dumps(output))
            else:
                #else statement for when cmd is clear
                await broadcast_queue.put(json.dumps(m))
           # msg = await ws.receive_text()
           # print(msg)
           # await broadcast_queue.put(msg)
    except Exception:
        pass
    finally:
        clients.discard(ws)


async def _broadcaster():
    while True:
        msg = await broadcast_queue.get()
        dead = []
        for c in list(clients):
            try:
                await c.send_text(msg)
            except Exception:
                dead.append(c)
        for c in dead:
            clients.discard(c)


@app.on_event("startup")
async def startup_event():
    global READINGS
    READINGS = await fetch_daily_material_object()
    asyncio.create_task(_broadcaster())

def send_command(payload: dict):
    loop = asyncio.get_event_loop()
    loop.call_soon_threadsafe(broadcast_queue.put_nowait, json.dumps(payload))
