import asyncio
import websockets
import json
from gtts import gTTS
import tempfile
import os

TEST_CASES = [
    {"lang_code": "hi", "text": "नमस्ते, आप कैसे हैं?", "desc": "Hindi", "target": "en"},
    {"lang_code": "bn", "text": "নমস্কার, আপনি কেমন আছেন?", "desc": "Bengali", "target": "hi"},
    {"lang_code": "ta", "text": "வணக்கம், நீங்கள் எப்படி இருக்கிறீர்கள்?", "desc": "Tamil", "target": "en"},
    {"lang_code": "te", "text": "నమస్కారం, మీరు ఎలా ఉన్నారు?", "desc": "Telugu", "target": "hi"},
    {"lang_code": "mr", "text": "नमस्कार, तुम्ही कसे आहात?", "desc": "Marathi", "target": "en"},
]

async def run_tests():
    uri = "ws://localhost:8000/ws/stream"
    
    for case in TEST_CASES:
        print(f"\n--- Testing Language: {case['desc']} ({case['lang_code']}) ---")
        
        # 1. Generate audio with gTTS
        print(f"Generating TTS audio for: {case['text']}")
        tts = gTTS(text=case['text'], lang=case['lang_code'])
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tts.save(f.name)
            audio_path = f.name
            
        try:
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
                
            # 2. Connect and send
            async with websockets.connect(uri) as websocket:
                # Set config: source_lang='auto', target_lang=case['target']
                config = {
                    "type": "config", 
                    "source_lang": "auto", 
                    "target_lang": case["target"]
                }
                await websocket.send(json.dumps(config))
                
                # Send binary audio
                print(f"Sending {len(audio_bytes)} bytes of audio data...")
                await websocket.send(audio_bytes)
                
                # Wait for response
                print("Waiting for response...")
                # We expect it to be fast now!
                response_str = await asyncio.wait_for(websocket.recv(), timeout=65.0)
                response = json.loads(response_str)
                
                if response.get("status") == "success":
                    print(f"✅ Success! Detected Language: {response.get('detected_lang')}")
                    print(f"Original text from ASR: {response.get('original_text')}")
                    print(f"Translated text to ({case['target']}): {response.get('translated_text')}")
                    if response.get("audio_response"):
                        print(f"Audio response received: {len(response.get('audio_response'))} base64 chars")
                else:
                    print(f"❌ Error response: {response}")
                    
        except Exception as e:
            print(f"❌ Error during test: {e}")
        finally:
            try:
                os.unlink(audio_path)
            except:
                pass

if __name__ == "__main__":
    asyncio.run(run_tests())
