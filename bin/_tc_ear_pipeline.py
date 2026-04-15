"""_tc_ear_pipeline — transcription + speaker-ID pipeline for tc-ear.

Takes a WAV file path, transcribes it with faster-whisper, identifies
the speaker via the tc-voice-identify CLI, and returns a result dict.
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import Optional

import soundfile as sf

# ---------------------------------------------------------------------------
# Lazy-loaded Whisper singleton
# ---------------------------------------------------------------------------

MODEL_SIZE = os.environ.get("TC_WHISPER_MODEL", "base.en")
_whisper_model = None


def _get_model():
    """Return a cached WhisperModel instance (loaded once per process)."""
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel

        _whisper_model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    return _whisper_model


# ---------------------------------------------------------------------------
# Speaker identification via tc-voice-identify CLI
# ---------------------------------------------------------------------------

def _identify_speaker(wav_path: str) -> tuple[str, float]:
    """Shell out to tc-voice-identify and return (speaker, confidence)."""
    try:
        result = subprocess.run(
            ["tc-voice-identify", "--json", wav_path],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return "Unknown", 0.0
        data = json.loads(result.stdout)
        return data.get("speaker", "Unknown"), float(data.get("confidence", 0.0))
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, json.JSONDecodeError, ValueError):
        return "Unknown", 0.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def process_utterance(wav_path: str) -> dict:
    """Transcribe a WAV file and identify the speaker.

    Returns {
        "transcript": str,       # transcribed text
        "speaker": str,          # speaker name or "Unknown"
        "confidence": float,     # cosine similarity score
        "duration_s": float,     # audio duration in seconds
    }
    """
    # Load audio
    signal, sr = sf.read(wav_path, dtype="float32")

    # Duration
    duration_s = len(signal) / sr

    # Transcribe (reuses singleton model)
    model = _get_model()
    segments, _ = model.transcribe(
        signal,
        language="en",
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
    )
    transcript = " ".join(s.text.strip() for s in segments).strip()

    # Speaker ID
    speaker, confidence = _identify_speaker(wav_path)

    return {
        "transcript": transcript,
        "speaker": speaker,
        "confidence": confidence,
        "duration_s": round(duration_s, 3),
    }
