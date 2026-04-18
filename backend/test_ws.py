import asyncio
import websockets
import json

async def test_ws():
    uri = "ws://localhost:8000/ws/stream"
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected successfully!")
            # Send a config message
            await websocket.send(json.dumps({"type": "config", "source_lang": "en", "target_lang": "hi"}))
            print("Config sent.")
            # Send dummy binary
            await websocket.send(b"dummy")
            print("Binary sent.")
            # Wait for response
            response = await websocket.recv()
            print(f"Response: {response}")
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    asyncio.run(test_ws())
