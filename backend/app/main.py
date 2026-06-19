import logging
import json
import base64
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from .core.security import decrypt_audio_data, encrypt_audio_data
from .services.translation_pipeline import pipeline
from .core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "TalkNWear AI Backend is running"}

@app.head("/")
async def root_head():
    return None

async def handle_audio_stream(websocket: WebSocket):
    await websocket.accept()
    logger.info("New wearable connected via WebSocket")
    
    # Session state for target/source language
    session_config = {
        "source_lang": "auto",
        "target_lang": "hi"
    }
    
    try:
        while True:
            try:
                # 1. Receive data - can be binary (speech) or text (config)
                message = await websocket.receive()
                
                if "bytes" in message:
                    # Direct binary audio data from MediaRecorder
                    audio_data = message["bytes"]
                    logger.info(f"Received binary audio: {len(audio_data)} bytes")
                    
                    # Use the current session's language configuration
                    result = await pipeline.process_audio_chunk(
                        audio_data, 
                        session_config["source_lang"], 
                        session_config["target_lang"]
                    )
                    
                    if result:
                        # 4. Return results with audio response
                        response = {
                            "original_text": result["original_text"],
                            "translated_text": result["translated_text"],
                            "detected_lang": result.get("detected_lang", "unknown"),
                            # Encode binary MP3 to base64 for browser playback
                            "audio_response": base64.b64encode(result["audio_output"]).decode('utf-8') if result.get("audio_output") else None,
                            "status": "success"
                        }
                        await websocket.send_text(json.dumps(response))
                    else:
                        # Pipeline returned None — send error so frontend doesn't hang
                        error_response = {
                            "status": "error",
                            "message": "Could not process speech. Try speaking louder or longer."
                        }
                        await websocket.send_text(json.dumps(error_response))
                
                elif "text" in message:
                    # Configuration updates from the frontend
                    try:
                        payload = json.loads(message["text"])
                        if payload.get("type") == "config":
                            session_config["source_lang"] = payload.get("source_lang", "auto")
                            session_config["target_lang"] = payload.get("target_lang", "hi")
                            logger.info(f"Updated session config: {session_config}")
                    except Exception as e:
                        logger.error(f"Config error: {str(e)}")
            
            except WebSocketDisconnect:
                logger.info("Wearable disconnected")
                break
            except Exception as e:
                logger.error(f"Error processing chunk: {str(e)}")
                # For critical errors, break the loop to avoid infinite error logs
                if "receive" in str(e).lower() or "closed" in str(e).lower():
                    break
                continue
                
    except WebSocketDisconnect:
        logger.info("Wearable disconnected")
    except Exception as e:
        logger.error(f"WebSocket global error: {str(e)}")
    finally:
        # Final cleanup attempt
        try:
            # Check if socket is still open before trying to close it
            if websocket.client_state.name != "DISCONNECTED":
                await websocket.close()
        except:
            pass

@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await handle_audio_stream(websocket)

@app.websocket("/")
async def websocket_root_endpoint(websocket: WebSocket):
    await handle_audio_stream(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

