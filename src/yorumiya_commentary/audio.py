from __future__ import annotations

from collections.abc import Callable
from math import sqrt

from .models import AudioChunk, AudioFeatures, Transcript, VadResult


class WhisperTranscriber:
    def __init__(self, adapter: Callable[[AudioChunk], Transcript] | None = None):
        self.adapter = adapter

    def transcribe(self, chunk: AudioChunk) -> Transcript:
        if self.adapter:
            return self.adapter(chunk)
        return Transcript(
            timestamp=chunk.timestamp,
            text="",
            start=chunk.timestamp,
            end=chunk.timestamp + len(chunk.samples) / max(chunk.sample_rate, 1),
            confidence=0.0,
        )


class VoiceActivityDetector:
    def __init__(self, threshold: float = 0.025):
        self.threshold = threshold

    def detect(self, chunk: AudioChunk) -> VadResult:
        if not chunk.samples:
            return VadResult(timestamp=chunk.timestamp, is_speech=False, speech_ratio=0.0)
        active = sum(1 for sample in chunk.samples if abs(sample) >= self.threshold)
        ratio = active / len(chunk.samples)
        duration = len(chunk.samples) / max(chunk.sample_rate, 1)
        return VadResult(
            timestamp=chunk.timestamp,
            is_speech=ratio >= 0.12,
            speech_ratio=ratio,
            start=chunk.timestamp if ratio else None,
            end=chunk.timestamp + duration if ratio else None,
        )


class AudioAnalyzer:
    def analyze(self, chunk: AudioChunk) -> AudioFeatures:
        if not chunk.samples:
            return AudioFeatures(chunk.timestamp, rms=0.0, peak=0.0, loudness="silent", atmosphere="quiet")

        peak = max(abs(sample) for sample in chunk.samples)
        rms = sqrt(sum(sample * sample for sample in chunk.samples) / len(chunk.samples))
        loudness = "loud" if rms >= 0.25 else "medium" if rms >= 0.08 else "quiet"
        atmosphere = "excited" if peak >= 0.7 or rms >= 0.28 else "active" if rms >= 0.1 else "calm"
        event = "impact" if peak >= 0.85 else None
        return AudioFeatures(chunk.timestamp, rms=rms, peak=peak, loudness=loudness, atmosphere=atmosphere, event=event)
