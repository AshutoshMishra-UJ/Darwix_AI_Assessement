"""
Q4 — Replay Audio Script
Simulates a live call by streaming a WAV file to the audio pipeline at 1x speed.

Usage:
  # Replay a real WAV file
  python q4-live-insights/replay_audio.py --file path/to/call.wav --call-id demo-001

  # Generate a synthetic test WAV and replay it
  python q4-live-insights/replay_audio.py --generate-test --call-id demo-001

The script streams 20ms PCM chunks (16kHz, 16-bit, mono) via WebSocket to:
  ws://localhost:8001/ws/audio/{call_id}

Requires: websockets, python-dotenv, wave (stdlib)
"""

import argparse
import asyncio
import os
import struct
import wave
from pathlib import Path


PIPELINE_WS_URL = "ws://localhost:8001/ws/audio/{call_id}"
CHUNK_DURATION_MS = 20
SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2  # 16-bit
CHUNK_SAMPLES = int(SAMPLE_RATE * CHUNK_DURATION_MS / 1000)
CHUNK_BYTES = CHUNK_SAMPLES * SAMPLE_WIDTH * CHANNELS


def generate_test_wav(output_path: Path, duration_seconds: int = 90) -> Path:
    """Generate a synthetic test WAV file with simulated speech-like audio."""
    import math
    import random

    print(f"[replay] Generating {duration_seconds}s synthetic test WAV at {output_path}")
    total_samples = SAMPLE_RATE * duration_seconds

    with wave.open(str(output_path), "w") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLE_RATE)

        # Generate sine wave bursts (simulates speech segments)
        samples = []
        t = 0
        while t < total_samples:
            # Speech burst: 0.3–1.5s
            burst_len = int(SAMPLE_RATE * (0.3 + random.random() * 1.2))
            freq = 200 + random.randint(0, 300)  # voice frequency range
            for i in range(min(burst_len, total_samples - t)):
                val = int(8000 * math.sin(2 * math.pi * freq * (t + i) / SAMPLE_RATE))
                samples.append(struct.pack("<h", val))
            t += burst_len

            # Silence gap: 0.1–0.5s
            silence_len = int(SAMPLE_RATE * (0.1 + random.random() * 0.4))
            for _ in range(min(silence_len, total_samples - t)):
                samples.append(struct.pack("<h", 0))
            t += silence_len

        wf.writeframes(b"".join(samples))

    print(f"[replay] Synthetic WAV generated: {output_path} ({duration_seconds}s)")
    return output_path


async def replay_wav(wav_path: Path, call_id: str):
    """Stream WAV file to the pipeline at real-time speed."""
    try:
        import websockets
    except ImportError:
        print("ERROR: websockets not installed. Run: pip install websockets")
        return

    url = PIPELINE_WS_URL.format(call_id=call_id)

    print(f"[replay] Opening WAV: {wav_path}")
    with wave.open(str(wav_path), "rb") as wf:
        src_rate = wf.getframerate()
        total_frames = wf.getnframes()
        duration_s = total_frames / src_rate
        print(f"[replay] Duration: {duration_s:.1f}s | Sample rate: {src_rate}Hz | Channels: {wf.getnchannels()}")

        print(f"[replay] Connecting to {url}")
        async with websockets.connect(url) as ws:
            print(f"[replay] Connected — streaming at real-time speed...")
            frames_sent = 0
            while True:
                frames = wf.readframes(CHUNK_SAMPLES)
                if not frames:
                    break
                await ws.send(frames)
                frames_sent += len(frames) // SAMPLE_WIDTH
                await asyncio.sleep(CHUNK_DURATION_MS / 1000)

            print(f"[replay] Done. Sent {frames_sent} samples ({frames_sent / SAMPLE_RATE:.1f}s)")


def main():
    parser = argparse.ArgumentParser(description="Replay audio to Q4 pipeline")
    parser.add_argument("--file", type=str, help="Path to WAV file to replay")
    parser.add_argument("--generate-test", action="store_true", help="Generate synthetic test WAV and replay it")
    parser.add_argument("--call-id", type=str, default=f"replay-{int(__import__('time').time())}", help="Call ID for this session")
    parser.add_argument("--duration", type=int, default=90, help="Duration for synthetic test WAV (seconds)")
    args = parser.parse_args()

    if args.generate_test:
        test_wav = Path(__file__).parent / f"test_{args.call_id}.wav"
        generate_test_wav(test_wav, duration_seconds=args.duration)
        asyncio.run(replay_wav(test_wav, args.call_id))
    elif args.file:
        asyncio.run(replay_wav(Path(args.file), args.call_id))
    else:
        print("Usage:")
        print("  python q4-live-insights/replay_audio.py --file <path.wav> --call-id demo-001")
        print("  python q4-live-insights/replay_audio.py --generate-test --call-id demo-001")


if __name__ == "__main__":
    main()
