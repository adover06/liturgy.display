# liturgy.display
A reading management system controlled by a webpage "remote" and processed by voice recognition.

## Overview
liturgy.display shows scripture/reading text on screen and advances slides by voice recognition word count using the Vosk speech-recognition engine. Designed for simple setup and offline/edge operation.

## Features
- Offline speech recognition (Vosk)
- Configurable words-per-slide depending on screen size and preference
- Simple config in .env
- Basic support for USCCB readings (no API key required)

## Prerequisites
- Python 3.8+ (or adjust for your runtime)
- pip
- Microphone access on the host machine
- A Vosk model (downloaded and extracted locally)

Download models: https://alphacephei.com/vosk/models

## Installation
1. Clone repository
    ```
    git clone /path/to/liturgy.display
    cd liturgy.display
    ```
2. (Optional) Create and activate a virtualenv
    ```
    python -m venv venv
    source venv/bin/activate
    ```
3. Install dependencies
    ```
    pip install -r requirements.txt
    ```

## Configuration
Create a `.env` file in the project root with at least:
```
WORDS_PER_SLIDE=40
MODEL_PATH=/your/path/to/vosk/model
```
Optional configuration:
```
MICROPHONE_INDEX=0
```
- WORDS_PER_SLIDE: number of words shown per slide before auto-advance
- MODEL_PATH: path to the extracted Vosk model directory
- MICROPHONE_INDEX (optional): specific microphone device index to use. If not set, uses system default. Run the app once to see available devices listed at startup.

## Running
Start the app (example):
```
python main.py
```


## Troubleshooting
- Model not found: verify MODEL_PATH points to the extracted model folder
- Microphone issues: ensure OS microphone permissions are granted and the correct device is selected.