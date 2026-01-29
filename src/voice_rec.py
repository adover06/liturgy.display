import threading
import pyaudio
import json
import queue
from vosk import Model, KaldiRecognizer


from src.reading import get_material
from src.server import send_command

import os
from dotenv import load_dotenv
load_dotenv()

from collections import deque
from time import sleep


WORDS_PER_SLIDE = int(os.getenv("WORDS_PER_SLIDE"))
QUEUE_MAXSIZE = 50             

tempWordCount = 0
currentWordCount = 0
slidequeue = deque()
isReadingActive = False
recognition_lock = threading.Lock()


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

def process_recognized_words(currentCount: str):
    global currentWordCount
    global tempWordCount

    print("IS ACTIVE:", isReadingActive)
    if not isReadingActive:
        return
    
    # words = text.split()
    # print(f"[voice_rec] Words: +{len(words)}")
    if currentCount == tempWordCount:
        return
    tempWordCount = currentCount
    currentWordCount += currentCount#len(words)
    if currentWordCount >= WORDS_PER_SLIDE:
        tempWordCount = 0
        currentWordCount = 0
        send_next_slide()

def word_recogniser_worker(audio_queue: queue.Queue):
    model = Model(os.getenv("MODEL_PATH"))
    rec = KaldiRecognizer(model, 16000)
    committed_words = []
    last_partial_words = []
    global currentWordCount

    
    def common_prefix_len(a, b) -> int:
        n = min(len(a), len(b))
        i = 0
        while i < n and a[i] == b[i]:
            i += 1
        return i
    
    while True:
        try:
            data = audio_queue.get(timeout=0.5)
        except queue.Empty:
            continue
        if data:
            try:
                if rec.AcceptWaveform(data):
                    r = json.loads(rec.Result())
                    text = r.get("text", "").strip()
                    if text:
                        final_words = text.split()
                        committed_words.extend(final_words)
                        last_partial_words = []
                        live_count = len(committed_words)
                        print("[final]", text, " | live_count =", live_count)
                        # process_recognized_words(text)  # final, stable
                else:
                    p = json.loads(rec.PartialResult())
                    partial = p.get("partial", "").strip()
                    if partial:
                        current_partial_words = partial.split()
                        # (optional) compute delta vs last partial, for incremental UI updates
                        cp = common_prefix_len(last_partial_words, current_partial_words)
                        new_words = current_partial_words[cp:]

                        last_partial_words = current_partial_words

                        live_count = len(committed_words) + len(current_partial_words)
                        process_recognized_words(live_count)
                        print("[partial]", partial, " | +", new_words, " | live_count =", live_count)

                audio_queue.task_done()
            except Exception as e:
                print(f"Recognition error: {e}")
def audio_stream_worker(audio_queue: queue.Queue):
    mic = pyaudio.PyAudio()
    stream = mic.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8192)
    stream.start_stream()
    while True:

        data = stream.read(4096, exception_on_overflow = False)
        audio_queue.put(data, block=True)


def run_voice_recognition():

    audio_queue = queue.Queue(maxsize=QUEUE_MAXSIZE)

    recogniser_thread = threading.Thread(target=word_recogniser_worker, args=(audio_queue,))
    recogniser_thread.start()
    
    stream_thread = threading.Thread(target=audio_stream_worker, args=(audio_queue,))
    stream_thread.start()

    
if __name__ == "__main__":
    print("[voice_rec] Running standalone (testing only)")
    run_voice_recognition()
