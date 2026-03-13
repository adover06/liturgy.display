import json
import os
import threading
from collections import deque

from dotenv import load_dotenv
from vosk import KaldiRecognizer, Model

from src.reading import get_material
from src.server import send_command

load_dotenv()

WORDS_PER_SLIDE = int(os.getenv("WORDS_PER_SLIDE", "40"))

slide_title = ""
slidequeue = deque()
isReadingActive = False

_model = None
_recognizer = None
_audio_lock = threading.Lock()
_committed_word_count = 0
_last_partial_words = []
_last_live_word_count = 0
_word_anchor = 0


def _ensure_model():
    global _model
    if _model is None:
        model_path = os.getenv("MODEL_PATH")
        if not model_path:
            raise RuntimeError("MODEL_PATH is not set")
        _model = Model(model_path)


def _reset_word_tracking():
    global _committed_word_count
    global _last_partial_words
    global _last_live_word_count
    global _word_anchor
    _committed_word_count = 0
    _last_partial_words = []
    _last_live_word_count = 0
    _word_anchor = 0


def start_audio_session():
    global _recognizer
    with _audio_lock:
        _ensure_model()
        _recognizer = KaldiRecognizer(_model, 16000)
        _reset_word_tracking()
    print("[voice_rec] Audio session started")


def stop_audio_session():
    global _recognizer
    with _audio_lock:
        _recognizer = None
        _reset_word_tracking()
    print("[voice_rec] Audio session stopped")


async def load_slides_for_reading(reading_type: str):
    global slidequeue
    global isReadingActive
    global slide_title

    isReadingActive = True
    slidequeue.clear()
    with _audio_lock:
        _reset_word_tracking()
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

    if slidequeue:
        slide = slidequeue.popleft()
        send_command({"cmd": "set", "title": slide_title, "text": slide})
    else:
        print("[voice_rec] No more slides")
        stop_reading()


def stop_reading():
    global isReadingActive
    global slidequeue
    global slide_title

    isReadingActive = False
    slide_title = ""
    slidequeue.clear()
    with _audio_lock:
        _reset_word_tracking()

    send_command({"cmd": "set", "title": slide_title, "text": ""})


async def handle_command(cmd: str, title: str = "", text: str = ""):
    print(f"[voice_rec] Received command: {cmd}, title: {title}")

    if cmd == "show":
        reading_type = title
        if reading_type:
            await load_slides_for_reading(reading_type)

    elif cmd == "clear":
        stop_reading()
    elif cmd == "set":
        send_command({"cmd": "set", "title": title, "text": text})
    elif cmd in {"mic_start", "mic_stop", "mic_status", "mic_state"}:
        send_command({"cmd": cmd, "title": title, "text": text})


def _update_progress(live_word_count: int):
    global _last_live_word_count
    global _word_anchor

    if not isReadingActive:
        return

    if live_word_count < _last_live_word_count:
        _last_live_word_count = live_word_count
        return

    _last_live_word_count = live_word_count
    while isReadingActive and (_last_live_word_count - _word_anchor) >= WORDS_PER_SLIDE:
        _word_anchor += WORDS_PER_SLIDE
        send_next_slide()


def ingest_audio_chunk(data: bytes):
    global _committed_word_count
    global _last_partial_words

    if not data:
        return

    def common_prefix_len(a, b) -> int:
        n = min(len(a), len(b))
        i = 0
        while i < n and a[i] == b[i]:
            i += 1
        return i

    with _audio_lock:
        if _recognizer is None:
            return

        try:
            if _recognizer.AcceptWaveform(data):
                result = json.loads(_recognizer.Result())
                text = result.get("text", "").strip()
                if text:
                    _committed_word_count += len(text.split())
                    _last_partial_words = []
                live_count = _committed_word_count
            else:
                partial_result = json.loads(_recognizer.PartialResult())
                partial = partial_result.get("partial", "").strip()
                if partial:
                    current_partial_words = partial.split()
                    _last_partial_words = current_partial_words
                    live_count = _committed_word_count + len(current_partial_words)
                else:
                    live_count = _committed_word_count
        except Exception as exc:
            print(f"[voice_rec] Recognition error: {exc}")
            return

    _update_progress(live_count)
