import pyaudio
import json
from vosk import Model, KaldiRecognizer

from reading import get_material
from server import send_command

import os
from dotenv import load_dotenv
load_dotenv()

from collections import deque
from time import sleep

WORDS_PER_SLIDE = int(os.getenv("WORDS_PER_SLIDE"))

currentWordCount = 0
slidequeue = deque()
isReadingActive = False


async def load_slides_for_reading(reading_type: str):
    global slidequeue
    global isReadingActive
    isReadingActive = True
    print("IS ACTIVE:", isReadingActive)
    slidequeue.clear()
    slide_object = await get_material(reading_type, WORDS_PER_SLIDE)
    new_slides = slide_object.get("slides", [])
    
    for slide in new_slides:
        slidequeue.append(slide)

    print(f"[voice_rec] Fetched {len(new_slides)} slides for '{reading_type}'")

    send_next_slide()

def send_next_slide():
    global slidequeue
    global isReadingActive
    
    if slidequeue:
        slide = slidequeue.popleft()
        send_command({"cmd": "set", "title": "", "text": slide})
    else:
        print("[voice_rec] No more slides")
        isReadingActive = False
        send_command({"cmd": "set", "title": "", "text": "End of Reading"})

def stop_reading():
    global isReadingActive
    global currentWordCount
    global slidequeue
    
    isReadingActive = False
    currentWordCount = 0
    slidequeue.clear()

    send_command({"cmd": "set", "title": "", "text": ""})


async def handle_command(cmd: str, title: str):
    print(f"[voice_rec] Received command: {cmd}, title: {title}")
    
    if cmd == "show":
        reading_type = title
        if reading_type:
            await load_slides_for_reading(reading_type)
    
    elif cmd == "clear":
        stop_reading()

def process_recognized_words(text: str):
    global currentWordCount
    print("IS ACTIVE:", isReadingActive)
    if not isReadingActive:
        return
    
    words = text.split()
    print(f"[voice_rec] Words: +{len(words)}")
    currentWordCount += len(words)
    if currentWordCount >= WORDS_PER_SLIDE:
        currentWordCount = 0
        send_next_slide()
    


def run_voice_recognition():

    print("[voice_rec] Initializing Vosk...")
    model = Model(os.getenv("MODEL_PATH"))
    rec = KaldiRecognizer(model, 16000)

    mic = pyaudio.PyAudio()
    stream = mic.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8192)
    stream.start_stream()
    
    print("[voice_rec] Listening for speech...")
    while True:
        data = stream.read(4096, exception_on_overflow = False)
        if rec.AcceptWaveform(data):
            result = rec.Result()
            result_dict = json.loads(result)
            text = result_dict.get("text", "")
            if text:
                print(f"[voice_rec] Recognized: {text}")
                process_recognized_words(text)
    #try:
    #    emu_word = "hello"
    #    print("[voice_rec] Emulating speech: emitting one word per second. Press Ctrl+C to stop.")
    #    while True:
    #        sleep(1)
    #        print(f"[voice_rec] Emulated word: {emu_word}")
    #        process_recognized_words(emu_word)
    #except KeyboardInterrupt:
    #    print("[voice_rec] Emulation stopped by user")
    #finally:
    #    try:
    #        stream.stop_stream()
    #        stream.close()
    #        mic.terminate()
    #    except Exception:
    #        pass
    #    print("[voice_rec] Audio stream closed (emulation)")


# For standalone testing only - normally use main.py
if __name__ == "__main__":
    print("[voice_rec] Running standalone (testing only)")
    run_voice_recognition()
