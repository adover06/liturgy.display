@echo off
setlocal

echo --- Detecting audio input devices ---
python -c "import pyaudio; mic=pyaudio.PyAudio(); [print(f'  [{i}] {mic.get_device_info_by_index(i)[\"name\"]}') for i in range(mic.get_device_count()) if mic.get_device_info_by_index(i).get('maxInputChannels',0)>0]; mic.terminate()" 2>nul
if errorlevel 1 (
    echo WARNING: Could not list audio devices. Enter device index manually.
)

echo.
set /p MIC_INDEX=Enter mic device index:

echo %MIC_INDEX%| findstr /r "^[0-9][0-9]*$" >nul
if errorlevel 1 (
    echo ERROR: Invalid device index "%MIC_INDEX%"
    exit /b 1
)

python -c "
import re, sys
idx = sys.argv[1]
path = '.env'
with open(path, 'r') as f:
    content = f.read()
if re.search(r'^MIC_DEVICE_INDEX=', content, re.MULTILINE):
    content = re.sub(r'^MIC_DEVICE_INDEX=.*', f'MIC_DEVICE_INDEX={idx}', content, flags=re.MULTILINE)
else:
    content = content.rstrip('\n') + '\nMIC_DEVICE_INDEX=' + idx + '\n'
with open(path, 'w') as f:
    f.write(content)
print(f'--- Mic device index set to {idx} ---')
" %MIC_INDEX%

echo.
docker-compose up %*
