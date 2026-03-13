#!/bin/bash

# List available audio input devices and prompt user to select one
echo "--- Detecting audio input devices ---"
DEVICE_LIST=$(python3 -c "
import pyaudio
mic = pyaudio.PyAudio()
for i in range(mic.get_device_count()):
    info = mic.get_device_info_by_index(i)
    if info.get('maxInputChannels', 0) > 0:
        print(f\"{i}: {info['name']}\")
mic.terminate()
" 2>/dev/null) || true

if [ -z "$DEVICE_LIST" ]; then
    OS="$(uname -s)"
    if [ "$OS" = "Linux" ] && command -v arecord >/dev/null 2>&1; then
        echo "(pyaudio unavailable — showing ALSA devices via arecord)"
        arecord -l 2>/dev/null || echo "WARNING: Could not list audio devices. Enter device index manually."
    elif [ "$OS" = "Darwin" ]; then
        echo "(pyaudio unavailable — showing audio devices via system_profiler)"
        system_profiler SPAudioDataType 2>/dev/null | grep -A2 "Input:" | grep -v "^--$" || echo "WARNING: Could not list audio devices. Enter device index manually."
    else
        echo "WARNING: Could not list audio devices. Enter device index manually."
    fi
else
    echo "$DEVICE_LIST"
fi

echo ""
printf "Enter mic device index: "
read -r MIC_INDEX

# Validate it's a number
case "$MIC_INDEX" in
    ''|*[!0-9]*)
        echo "ERROR: Invalid device index '$MIC_INDEX'"
        exit 1
        ;;
esac

# Write MIC_DEVICE_INDEX into the root .env (add or update)
ENV_FILE="$(dirname "$0")/.env"
if grep -q "^MIC_DEVICE_INDEX=" "$ENV_FILE"; then
    sed -i.bak "s/^MIC_DEVICE_INDEX=.*/MIC_DEVICE_INDEX=$MIC_INDEX/" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
else
    echo "MIC_DEVICE_INDEX=$MIC_INDEX" >> "$ENV_FILE"
fi

echo "--- Mic device index set to $MIC_INDEX ---"
echo ""

docker-compose up "$@"
