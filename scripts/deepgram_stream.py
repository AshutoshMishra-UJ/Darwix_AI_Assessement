"""Deepgram streaming bridge for 16-bit PCM websocket audio.

Usage:
    python scripts/deepgram_stream.py

The browser/replay client sends binary PCM frames to `/ws/audio/{call_id}`.
Deepgram returns interim/final transcript events, which are broadcast to the dashboard.
"""

import asyncio
import json
import os
from pathlib import Path

import websockets
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
DEEPGRAM_KEY = os.getenv("DEEPGRAM_API_KEY", "").strip()
DEEPGRAM_URL = "wss://api.deepgram.com/v1/listen?encoding=linear16&sample_rate=16000&channels=1&interim_results=true&punctuate=true&diarize=true&model=nova-3&language=en"
app = FastAPI(title="Aegis Deepgram Stream")


@app.get("/health")
def health():
    return {"status": "ok", "deepgram_configured": bool(DEEPGRAM_KEY)}


@app.websocket("/ws/audio/{call_id}")
async def audio_stream(websocket: WebSocket, call_id: str):
    await websocket.accept()
    if not DEEPGRAM_KEY:
        await websocket.send_json({"type": "error", "message": "DEEPGRAM_API_KEY is not configured"})
        await websocket.close()
        return
    headers = {"Authorization": f"Token {DEEPGRAM_KEY}"}
    try:
        async with websockets.connect(DEEPGRAM_URL, additional_headers=headers) as deepgram:
            async def forward_audio():
                while True:
                    frame = await websocket.receive_bytes()
                    await deepgram.send(frame)

            async def forward_transcripts():
                async for raw in deepgram:
                    message = json.loads(raw)
                    await websocket.send_json({"type": "transcript", "call_id": call_id, "payload": message})

            await asyncio.gather(forward_audio(), forward_transcripts())
    except (WebSocketDisconnect, websockets.WebSocketException, asyncio.IncompleteReadError):
        return


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("deepgram_stream:app", host="127.0.0.1", port=8003)
