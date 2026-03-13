#!/bin/bash
set -e

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
" 2>/dev/null)

if [ -z "$DEVICE_LIST" ]; then
    echo "WARNING: Could not list audio devices. Enter device index manually."
else
    echo "$DEVICE_LIST"
fi

echo ""
read -p "Enter mic device index: " MIC_INDEX

# Validate it's a number
if ! [[ "$MIC_INDEX" =~ ^[0-9]+$ ]]; then
    echo "ERROR: Invalid device index '$MIC_INDEX'"
    exit 1
fi

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
