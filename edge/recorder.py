import asyncio
import websockets
import json
import base64
import os
import time
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Config (matching backend settings for prototype)
AUDIO_ENCRYPTION_KEY = "32byte_long_encryption_key_12345"
BACKEND_URL = "ws://localhost:8000/ws/stream"

class TalkNWearEdge:
    def __init__(self):
        self.aesgcm = AESGCM(AUDIO_ENCRYPTION_KEY.encode())

    def encrypt_data(self, data: bytes) -> str:
        nonce = os.urandom(12)
        ct = self.aesgcm.encrypt(nonce, data, None)
        return base64.b64encode(nonce + ct).decode('utf-8')

    async def stream_audio(self):
        print(f"Connecting to {BACKEND_URL}...")
        try:
            async with websockets.connect(BACKEND_URL) as websocket:
                print("Connected! Initializing wearable streaming...")
                
                # Simulation Loop: Capture audio and stream
                # In real scenario, would use sounddevice or pyaudio
                while True:
                    print("\n[Wearable] Listening... (Press Ctrl+C to stop)")
                    time.sleep(1) # Simulate waiting for voice trigger
                    
                    # 1. Capture/Simulate audio chunk
                    raw_audio = b"SIMULATED_PCM_AUDIO_DATA_CHUNK" 
                    
                    # 2. Encrypt (Government-grade requirement)
                    encrypted_payload = self.encrypt_data(raw_audio)
                    
                    # 3. Pack and Send
                    message = {
                        "audio": encrypted_payload,
                        "source_lang": "hi", # Example: Defaulting to Hindi
                        "target_lang": "en",
                        "device_id": "TW-001-PROTOTYPE"
                    }
                    
                    await websocket.send(json.dumps(message))
                    print(f"[Wearable] Streamed chunk. Size: {len(encrypted_payload)} bytes")
                    
                    # 4. Handle Response (Visual/Audio feedback)
                    response = await websocket.recv()
                    data = json.loads(response)
                    print(f"[Backend] Translated: {data['translated_text']}")
                    
                    time.sleep(2) # Interval between captures

        except Exception as e:
            print(f"Connection error: {e}")

if __name__ == "__main__":
    edge = TalkNWearEdge()
    try:
        asyncio.run(edge.stream_audio())
    except KeyboardInterrupt:
        print("\nWearable shutting down.")
