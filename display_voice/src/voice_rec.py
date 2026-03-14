import json
import logging
import os
import threading
from collections import deque

from dotenv import load_dotenv
from vosk import KaldiRecognizer, Model

from src.reading import get_material
from src.server import send_command

load_dotenv()
logger = logging.getLogger("display.voice")

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
_audio_chunk_counter = 0


def _ensure_model():
    global _model
    if _model is None:
        model_path = os.getenv("MODEL_PATH")
        if not model_path:
            raise RuntimeError("MODEL_PATH is not set")
        logger.debug("Loading Vosk model from path=%s", model_path)
        _model = Model(model_path)
        logger.debug("Vosk model loaded successfully")


def _reset_word_tracking():
    global _committed_word_count
    global _last_partial_words
    global _last_live_word_count
    global _word_anchor
    global _audio_chunk_counter
    _committed_word_count = 0
    _last_partial_words = []
    _last_live_word_count = 0
    _word_anchor = 0
    _audio_chunk_counter = 0


def start_audio_session():
    global _recognizer
    model_path = os.getenv("MODEL_PATH", "")
    try:
        with _audio_lock:
            _ensure_model()
            _recognizer = KaldiRecognizer(_model, 16000)
            _reset_word_tracking()
        logger.debug("Audio recognition session started model_path=%s", model_path)
        send_command(
            {"cmd": "mic_backend", "title": "model_loaded", "text": model_path}
        )
    except Exception as exc:
        logger.exception("Audio session start failed: %s", exc)
        send_command(
            {"cmd": "mic_backend", "title": "model_load_error", "text": str(exc)}
        )
        raise


def stop_audio_session():
    global _recognizer
    with _audio_lock:
        _recognizer = None
        _reset_word_tracking()
    logger.debug("Audio recognition session stopped")
    send_command(
        {
            "cmd": "mic_backend",
            "title": "audio_stopped",
            "text": "Audio session stopped",
        }
    )


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

    logger.info(
        "Fetched slides count=%s reading_type=%s", len(new_slides), reading_type
    )

    send_next_slide()


def send_next_slide():
    global slidequeue
    global isReadingActive

    if slidequeue:
        slide = slidequeue.popleft()
        send_command({"cmd": "set", "title": slide_title, "text": slide})
    else:
        logger.info("No more slides; stopping reading")
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
    noisy_commands = {
        "mic_state",
        "mic_backend",
        "mic_metrics",
        "mic_detect",
        "mic_status",
    }
    if cmd in noisy_commands:
        logger.debug("Command received cmd=%s title=%s", cmd, title)
    else:
        logger.info("Command received cmd=%s title=%s", cmd, title)

    if cmd == "show":
        reading_type = title
        if reading_type:
            await load_slides_for_reading(reading_type)

    elif cmd == "clear":
        stop_reading()
    elif cmd == "set":
        send_command({"cmd": "set", "title": title, "text": text})
    elif cmd == "mic_status":
        with _audio_lock:
            model_loaded = _model is not None
        if model_loaded:
            send_command(
                {
                    "cmd": "mic_backend",
                    "title": "model_loaded",
                    "text": os.getenv("MODEL_PATH", ""),
                }
            )
        else:
            send_command(
                {
                    "cmd": "mic_backend",
                    "title": "model_not_loaded",
                    "text": "Model loads when stream starts.",
                }
            )
    elif cmd in {
        "mic_start",
        "mic_stop",
        "mic_state",
        "mic_backend",
        "mic_metrics",
        "mic_detect",
    }:
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
        logger.info(
            "Slide advance trigger live_count=%s anchor=%s words_per_slide=%s",
            _last_live_word_count,
            _word_anchor,
            WORDS_PER_SLIDE,
        )
        send_next_slide()


def ingest_audio_chunk(data: bytes):
    global _committed_word_count
    global _last_partial_words
    global _audio_chunk_counter

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
            _audio_chunk_counter += 1
            if _audio_chunk_counter % 100 == 0:
                logger.debug(
                    "Audio ingest stats chunks=%s chunk_bytes=%s committed_words=%s",
                    _audio_chunk_counter,
                    len(data),
                    _committed_word_count,
                )

            if _recognizer.AcceptWaveform(data):
                result = json.loads(_recognizer.Result())
                text = result.get("text", "").strip()
                if text:
                    _committed_word_count += len(text.split())
                    _last_partial_words = []
                    logger.debug(
                        "Microphone final_detected text=%s committed_words=%s",
                        text,
                        _committed_word_count,
                    )
                    send_command({"cmd": "mic_detect", "title": "final", "text": text})
                live_count = _committed_word_count
            else:
                partial_result = json.loads(_recognizer.PartialResult())
                partial = partial_result.get("partial", "").strip()
                if partial:
                    current_partial_words = partial.split()
                    _last_partial_words = current_partial_words
                    live_count = _committed_word_count + len(current_partial_words)
                    if _audio_chunk_counter % 50 == 0:
                        logger.debug(
                            "Microphone partial_detected text=%s live_count=%s reading_active=%s",
                            partial,
                            live_count,
                            isReadingActive,
                        )
                        send_command(
                            {"cmd": "mic_detect", "title": "partial", "text": partial}
                        )
                else:
                    live_count = _committed_word_count
        except Exception as exc:
            logger.exception("Recognition error: %s", exc)
            send_command(
                {"cmd": "mic_backend", "title": "recognition_error", "text": str(exc)}
            )
            return

    _update_progress(live_count)
