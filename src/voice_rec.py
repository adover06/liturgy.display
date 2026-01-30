import threading
import pyaudio
import json
import queue
from collections import deque
from vosk import Model, KaldiRecognizer

#load reading module
from src.reading import get_material
from src.server import send_command

#load environment variables
import os
from dotenv import load_dotenv
load_dotenv()

WORDS_PER_SLIDE = int(os.getenv("WORDS_PER_SLIDE"))
MICROPHONE_INDEX = os.getenv("MICROPHONE_INDEX")  # Optional mic selection
QUEUE_MAXSIZE = 50

committed_words = []
last_partial_words = []

slide_title = ""
slidequeue = deque()
isReadingActive = False
current_slide_word_count = 0  # Track expected words in current slide

async def load_slides_for_reading(reading_type: str):
    global slidequeue
    global isReadingActive
    global committed_words
    global slide_title
    
    committed_words = []
    isReadingActive = True
    slidequeue.clear()
    slide_object = await get_material(reading_type, WORDS_PER_SLIDE)
    new_slides = slide_object.get("slides", [])
    slide_title = slide_object.get("title", "")
    
    for slide in new_slides:
        slidequeue.append(slide)

    print(f"[voice_rec] Fetched {len(new_slides)} slides for '{reading_type}'")

    send_next_slide()

def send_next_slide():
    global slidequeue
    global isReadingActive
    global current_slide_word_count
    
    if slidequeue:
        slide = slidequeue.popleft()
        # Count the actual words in this slide
        current_slide_word_count = len(slide.split())
        print(f"[voice_rec] Sending slide with {current_slide_word_count} words")
        send_command({"cmd": "set", "title": slide_title, "text": slide})
    else:
        print("[voice_rec] No more slides")
        stop_reading()

def stop_reading():
    global isReadingActive
    global currentWordCount
    global slidequeue
    global slide_title
    global current_slide_word_count
    
    isReadingActive = False
    slide_title = ""
    currentWordCount = []
    slidequeue.clear()
    current_slide_word_count = 0

    send_command({"cmd": "set", "title": slide_title, "text": ""})


async def handle_command(cmd: str, title: str):
    print(f"[voice_rec] Received command: {cmd}, title: {title}")
    
    if cmd == "show":
        reading_type = title
        if reading_type:
            await load_slides_for_reading(reading_type)
    
    elif cmd == "clear":
        stop_reading()

def process_words(currentCount: str):
    global committed_words
    global current_slide_word_count

    print(f"[voice_rec] Committed words: {committed_words}")
    if not isReadingActive:
        return
    
    temp_word_count = len(committed_words)
    # Use the actual word count of the current slide instead of WORDS_PER_SLIDE
    # This handles the case where the last slide has fewer words
    if temp_word_count >= current_slide_word_count:
        committed_words = []
        send_next_slide()

def word_recogniser_worker(audio_queue: queue.Queue):
    model = Model(os.getenv("MODEL_PATH"))
    rec = KaldiRecognizer(model, 16000)
    global committed_words
    global last_partial_words 
    
    def common_prefix_len(a, b) -> int:
        n = min(len(a), len(b))
        i = 0
        while i < n and a[i] == b[i]:
            i += 1
        return i
    
    while True:
        if isReadingActive:
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
                            last_partial_words = []
                            process_words(text)  # final, stable
                    else:
                        p = json.loads(rec.PartialResult())
                        partial = p.get("partial", "").strip()
                        if partial:
                            current_partial_words = partial.split()
                            # (optional) compute delta vs last partial, for incremental UI updates
                            cp = common_prefix_len(last_partial_words, current_partial_words)
                            new_words = current_partial_words[cp:]
                            committed_words.extend(new_words)
                            last_partial_words = current_partial_words

                            live_count = len(committed_words) + len(current_partial_words)
                            process_words(live_count)

                    audio_queue.task_done()
                except Exception as e:
                    print(f"Recognition error: {e}")
def audio_stream_worker(audio_queue: queue.Queue):
    mic = pyaudio.PyAudio()
    
    # Use specified microphone index if provided, otherwise use default
    input_device_index = None
    if MICROPHONE_INDEX is not None:
        try:
            input_device_index = int(MICROPHONE_INDEX)
            print(f"[voice_rec] Using microphone index: {input_device_index}")
        except ValueError:
            print(f"[voice_rec] Invalid MICROPHONE_INDEX '{MICROPHONE_INDEX}', using default mic")
    else:
        print("[voice_rec] Using default microphone")
    
    stream = mic.open(
        format=pyaudio.paInt16, 
        channels=1, 
        rate=16000, 
        input=True, 
        frames_per_buffer=8192,
        input_device_index=input_device_index
    )
    stream.start_stream()
    while True:
        data = stream.read(4096, exception_on_overflow = False)
        audio_queue.put(data, block=True)

def run_voice_recognition():
    # List available audio devices for debugging
    mic = pyaudio.PyAudio()
    print("[voice_rec] Available audio input devices:")
    for i in range(mic.get_device_count()):
        info = mic.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0:
            print(f"  [{i}] {info['name']}")
    mic.terminate()

    audio_queue = queue.Queue(maxsize=QUEUE_MAXSIZE)

    recogniser_thread = threading.Thread(target=word_recogniser_worker, args=(audio_queue,))
    recogniser_thread.start()
    
    stream_thread = threading.Thread(target=audio_stream_worker, args=(audio_queue,))
    stream_thread.start()
    
if __name__ == "__main__":
    print("[voice_rec] Running standalone")
    run_voice_recognition()
