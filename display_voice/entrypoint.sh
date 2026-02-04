#!/bin/bash
set -e

MODEL_PATH=${MODEL_PATH:-"/app/vosk-model"}
MODEL_URL=${VOSK_MODEL_URL:-"https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"}

# Check if the model directory is empty
if [ ! -d "$MODEL_PATH/am" ] && [ ! -d "$MODEL_PATH/conf" ]; then
    echo "--- Model not found. Downloading from $MODEL_URL ---"
    mkdir -p "$MODEL_PATH"
    cd /tmp
    wget -qO model.zip "$MODEL_URL"
    unzip -q model.zip
    # Move the extracted model contents (handles the vosk-model-* directory wrapper)
    extracted_dir=$(ls -d vosk-model-* 2>/dev/null | head -1)
    if [ -z "$extracted_dir" ]; then
        echo "ERROR: Failed to find extracted model directory"
        exit 1
    fi
    mv "$extracted_dir"/* "$MODEL_PATH/"
    rm -rf "$extracted_dir" model.zip
    echo "--- Model setup complete. ---"
else
    echo "--- Model found. Skipping download. ---"
fi

exec "$@"