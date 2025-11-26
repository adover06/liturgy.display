import threading
import uvicorn

import server
import src.voice_rec as voice_rec

def main():
    print("[main] Starting liturgy display app...")
    
    
    voice_thread = threading.Thread(target=voice_rec.run_voice_recognition, daemon=True)
    voice_thread.start()
    print("[main] Voice recognition thread started")
    

    print("[main] Starting server on http://0.0.0.0:8000")
    uvicorn.run(server.app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
