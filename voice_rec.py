import sounddevice as sd
import queue, json
from vosk import Model, KaldiRecognizer

import asyncio
from reading import fetch_daily_material_object

model = Model("models")
rec = KaldiRecognizer(model,16000)

q = queue.Queue()

def callback(indata, frames, time, status):
    if status:
        print(status, flush=True)
    q.put(bytes(indata))

with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16', channels=1, callback=callback):
    print("Listening... (press Ctrl+C to stop)")
    while True:
        data = q.get()
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            text = result.get("text", "").lower()
            print("Heard:", text)
            if "the gospel according" in text:
                print(">>> TRIGGER WORD DETECTED! <<<")
                print("Processing...")
                print("Fetching readings object...")
                material = asyncio.run(fetch_daily_material_object())
                print("\n\n")
                print(material["Gospel"])

        else:
            partial = json.loads(rec.PartialResult())

