import pyaudio
import queue, json
from vosk import Model, KaldiRecognizer
from reading import daily_keyword_fetch
import asyncio


model = Model(r"/Users/andrewdover/Documents/liturgy.display/models")
rec = KaldiRecognizer(model,16000)

mic = pyaudio.PyAudio()
stream = mic.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8192)
stream.start_stream()   

keywords = asyncio.run(daily_keyword_fetch()) 

print(f"Keywords: {keywords}")


def search_for_keyword(text):
    for keyword in keywords:
        print(text.lower())
        if keyword in text.lower():
            print(f"Keyword '{keyword}' was detected")
    

while True:
    data = stream.read(4096, exception_on_overflow = False)
    if rec.AcceptWaveform(data):
        text = rec.Result()
        text = text[14:-3]
        #print(text)
        search_for_keyword(text)


  


