"""
Audio capture + VAD module for tc-ear daemon.

Captures audio from the default mic at 16kHz mono, applies energy-based
voice activity detection (RMS on ~30ms frames), and yields complete
utterances as WAV bytes.
"""

import collections
import io
import wave
from datetime import datetime

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"
FRAME_MS = 30
FRAME_SAMPLES = int(SAMPLE_RATE * FRAME_MS / 1000)  # 480 samples
PREROLL_MS = 200
PREROLL_FRAMES = max(1, PREROLL_MS // FRAME_MS)  # ~7 frames


def _rms(frame: np.ndarray) -> float:
    """Compute RMS of a 16-bit integer audio frame, normalized to [0, 1]."""
    floats = frame.astype(np.float32) / 32768.0
    return float(np.sqrt(np.mean(floats ** 2)))


def _pack_wav(frames: list[np.ndarray]) -> bytes:
    """Pack a list of int16 numpy frames into WAV bytes (16-bit PCM, 16kHz, mono)."""
    audio = np.concatenate(frames)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())
    return buf.getvalue()


def utterance_stream(
    device=None,
    threshold=0.02,
    min_speech_ms=500,
    min_silence_ms=700,
    min_utterance_s=0.8,
):
    """
    Generator that yields (start_iso: str, end_iso: str, wav_bytes: bytes)
    for each detected utterance.

    - device: sounddevice device index (None = default)
    - threshold: RMS threshold for speech detection
    - min_speech_ms: minimum speech duration before we consider it an utterance
    - min_silence_ms: silence duration to end an utterance
    - min_utterance_s: minimum total utterance duration (skip shorter ones as noise)
    """
    min_speech_frames = max(1, min_speech_ms // FRAME_MS)
    min_silence_frames = max(1, min_silence_ms // FRAME_MS)

    # Pre-roll ring buffer keeps recent frames so word onsets aren't clipped
    preroll = collections.deque(maxlen=PREROLL_FRAMES)

    # State machine
    IDLE, SPEAKING = 0, 1
    state = IDLE

    speech_frame_count = 0
    silence_frame_count = 0
    utterance_frames: list[np.ndarray] = []
    start_time: str | None = None

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype=DTYPE,
        blocksize=FRAME_SAMPLES,
        device=device,
    ) as stream:
        while True:
            data, overflowed = stream.read(FRAME_SAMPLES)
            frame = data[:, 0].copy()  # mono: take first channel
            energy = _rms(frame)
            is_speech = energy > threshold

            if state == IDLE:
                if is_speech:
                    speech_frame_count += 1
                else:
                    speech_frame_count = 0

                # Always maintain the pre-roll buffer
                preroll.append(frame)

                if speech_frame_count >= min_speech_frames:
                    # Transition to SPEAKING — include pre-roll
                    state = SPEAKING
                    start_time = datetime.now().isoformat()
                    utterance_frames = list(preroll)
                    preroll.clear()
                    silence_frame_count = 0

            elif state == SPEAKING:
                utterance_frames.append(frame)

                if is_speech:
                    silence_frame_count = 0
                else:
                    silence_frame_count += 1

                if silence_frame_count >= min_silence_frames:
                    # Transition back to IDLE
                    end_time = datetime.now().isoformat()
                    duration_s = len(utterance_frames) * FRAME_MS / 1000.0

                    if duration_s >= min_utterance_s:
                        wav_bytes = _pack_wav(utterance_frames)
                        yield (start_time, end_time, wav_bytes)

                    # Reset
                    state = IDLE
                    speech_frame_count = 0
                    silence_frame_count = 0
                    utterance_frames = []
                    start_time = None
                    preroll.clear()
