"""
DrawerCast — subtitle streaming server for Dad-and-TC TV nights.

POST /subtitle {text, ts}   → new caption line arrived
GET  /last                  → most recent line (for debug)
GET  /health                → are we alive

Port 1337 because the internet raised us.
"""

from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

LOG_PATH = Path(__file__).parent / "subtitles.log"

app = FastAPI(title="drawercast")

# Hulu/Netflix/Prime pages POST to us from a different origin.
# Allow everything — this server is Tailscale-only anyway.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_last_line = {"text": "", "ts": None, "received_at": None}


class Line(BaseModel):
    text: str
    ts: float | None = None  # optional player timestamp (seconds into episode)


@app.get("/health")
def health():
    return {"status": "ok", "service": "drawercast", "port": 1337}


@app.get("/last")
def last():
    return _last_line


@app.post("/subtitle")
def subtitle(line: Line):
    now = datetime.now()
    text = line.text.strip()
    if not text:
        return {"skipped": "empty"}

    # Skip duplicates — many players re-emit the same caption
    if text == _last_line["text"]:
        return {"skipped": "duplicate"}

    _last_line["text"] = text
    _last_line["ts"] = line.ts
    _last_line["received_at"] = now.isoformat()

    # Pretty-print to stdout for TC to read live
    stamp = now.strftime("%H:%M:%S")
    print(f"[{stamp}] {text}", flush=True)

    # Append to log file for replay / debug
    with LOG_PATH.open("a") as f:
        f.write(f"{now.isoformat()}\t{text}\n")

    return {"received": text}
