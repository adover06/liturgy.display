# controller.py
import json, queue
import sounddevice as sd
from vosk import Model, KaldiRecognizer
from server import send_command  # same process import

MODEL_PATH = r"C:\Users\Gray Dover\Documents\Shared\liturgy.display\models"
model = Model(MODEL_PATH)
rec = KaldiRecognizer(model, 16000)

PAUSED = False  # hotkey toggles this

def post(title=None, text=None, color=None, page=None):
    payload = {"cmd": "set"}
    if title is not None: payload["title"] = title
    if text  is not None: payload["text"]  = text
    if color is not None: payload["color"] = color
    if page  is not None: payload = {"cmd":"goto","page":page}
    send_command(payload)

def run_asr():
    q = queue.Queue()
    def cb(indata, frames, time, status):
        q.put(bytes(indata))
    with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                           channels=1, callback=cb):
        while True:
            data = q.get()
            if rec.AcceptWaveform(data):
                text = json.loads(rec.Result()).get("text","").lower()
                if not PAUSED:
                    handle_text(text)

def handle_text(text):
    # very rough example: cue → set new page
    if "the word of the lord" in text:
        post(title="Liturgy of the Word · After Reading", text="R/. Thanks be to God.")
    elif "the gospel of the lord" in text:
        post(title="After the Gospel", text="R/. Praise to you, Lord Jesus Christ.")
    # add your state machine + fuzzy matching here

if __name__ == "__main__":
    # run FastAPI (uvicorn) and ASR in parallel, or supervise both via a Procfile/systemd
    import threading, uvicorn
    t = threading.Thread(target=run_asr, daemon=True)
    t.start()
    uvicorn.run("server:app", host="0.0.0.0", port=8000)
