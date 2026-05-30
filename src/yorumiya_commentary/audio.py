from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from math import sqrt
from typing import Any

from .models import AudioChunk, AudioFeatures, CommentaryEvent, Transcript, VadResult


TranscriptAdapterPayload = Transcript | dict[str, Any] | str | None


@dataclass(frozen=True)
class TranscriptPolicy:
    fallback_confidence: float = 0.0
    string_confidence: float = 0.5

    def __post_init__(self) -> None:
        if not 0 <= self.fallback_confidence <= 1:
            raise ValueError("fallback_confidence must be between 0 and 1")
        if not 0 <= self.string_confidence <= 1:
            raise ValueError("string_confidence must be between 0 and 1")


class WhisperTranscriber:
    def __init__(self, adapter: Callable[[AudioChunk], TranscriptAdapterPayload] | None = None, policy: TranscriptPolicy | None = None):
        self.adapter = adapter
        self.policy = policy or TranscriptPolicy()

    def transcribe(self, chunk: AudioChunk) -> Transcript:
        if self.adapter:
            return self.normalize(self.adapter(chunk), chunk)
        return self.empty_transcript(chunk)

    def empty_transcript(self, chunk: AudioChunk) -> Transcript:
        return Transcript(
            timestamp=chunk.timestamp,
            text="",
            start=chunk.timestamp,
            end=chunk.timestamp + len(chunk.samples) / max(chunk.sample_rate, 1),
            confidence=0.0,
        )

    def normalize(self, payload: TranscriptAdapterPayload, chunk: AudioChunk) -> Transcript:
        if payload is None:
            return self.empty_transcript(chunk)
        if isinstance(payload, Transcript):
            return self._normalize_transcript(payload)
        if isinstance(payload, str):
            return self._normalize_transcript(
                Transcript(
                    timestamp=chunk.timestamp,
                    text=payload,
                    start=chunk.timestamp,
                    end=chunk.timestamp + len(chunk.samples) / max(chunk.sample_rate, 1),
                    confidence=self.policy.string_confidence if payload else self.policy.fallback_confidence,
                )
            )
        if isinstance(payload, dict):
            return self._normalize_transcript(
                Transcript(
                    timestamp=float(payload.get("timestamp", chunk.timestamp)),
                    text=str(payload.get("text", "")),
                    start=float(payload.get("start", chunk.timestamp)),
                    end=float(payload.get("end", chunk.timestamp + len(chunk.samples) / max(chunk.sample_rate, 1))),
                    confidence=float(payload.get("confidence", self.policy.fallback_confidence)),
                )
            )
        raise TypeError("Transcript adapter must return Transcript, dict, str, or None")

    def _normalize_transcript(self, transcript: Transcript) -> Transcript:
        start = max(0.0, transcript.start)
        end = max(start, transcript.end)
        confidence = min(1.0, max(0.0, transcript.confidence))
        return Transcript(
            timestamp=transcript.timestamp,
            text=transcript.text.strip(),
            start=start,
            end=end,
            confidence=confidence,
        )


@dataclass(frozen=True)
class TranscriptEventDetectionPolicy:
    min_confidence: float = 0.65
    salience_scale: float = 0.6
    speak_threshold: float = 0.8

    def __post_init__(self) -> None:
        for name, value in (
            ("min_confidence", self.min_confidence),
            ("salience_scale", self.salience_scale),
            ("speak_threshold", self.speak_threshold),
        ):
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")


class TranscriptEventDetector:
    def __init__(self, policy: TranscriptEventDetectionPolicy | None = None):
        self.policy = policy or TranscriptEventDetectionPolicy()

    def detect(self, transcript: Transcript | None) -> CommentaryEvent | None:
        if transcript is None or not transcript.text:
            return None
        if transcript.confidence < self.policy.min_confidence:
            return None

        salience = min(1.0, transcript.confidence * self.policy.salience_scale)
        return CommentaryEvent(
            timestamp=transcript.timestamp,
            kind="transcript_signal",
            description="Transcript speech detected",
            salience=salience,
            should_speak=salience >= self.policy.speak_threshold,
            metadata={
                "source": "transcript",
                "confidence": transcript.confidence,
                "duration": max(0.0, transcript.end - transcript.start),
                "text_length": len(transcript.text),
            },
        )


@dataclass(frozen=True)
class VoiceActivityPolicy:
    threshold: float = 0.025
    min_speech_ratio: float = 0.12
    min_active_samples: int = 1

    def __post_init__(self) -> None:
        if self.threshold < 0:
            raise ValueError("threshold must be non-negative")
        if not 0 <= self.min_speech_ratio <= 1:
            raise ValueError("min_speech_ratio must be between 0 and 1")
        if self.min_active_samples < 0:
            raise ValueError("min_active_samples must be non-negative")


class VoiceActivityDetector:
    def __init__(self, threshold: float | None = None, policy: VoiceActivityPolicy | None = None):
        if policy and threshold is not None:
            raise ValueError("Specify either threshold or policy, not both")
        self.policy = policy or VoiceActivityPolicy(threshold=threshold if threshold is not None else 0.025)

    def detect(self, chunk: AudioChunk) -> VadResult:
        if not chunk.samples:
            return VadResult(timestamp=chunk.timestamp, is_speech=False, speech_ratio=0.0, reason="silent")
        active = sum(1 for sample in chunk.samples if abs(sample) >= self.policy.threshold)
        ratio = active / len(chunk.samples)
        duration = len(chunk.samples) / max(chunk.sample_rate, 1)
        is_speech = ratio >= self.policy.min_speech_ratio and active >= self.policy.min_active_samples
        reason = "speech_detected" if is_speech else "no_active_samples" if active == 0 else "low_activity"
        return VadResult(
            timestamp=chunk.timestamp,
            is_speech=is_speech,
            speech_ratio=ratio,
            start=chunk.timestamp if active else None,
            end=chunk.timestamp + duration if active else None,
            reason=reason,
            active_samples=active,
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


@dataclass(frozen=True)
class AudioEventDetectionPolicy:
    speak_threshold: float = 0.45
    impact_salience: float = 0.85
    excited_salience: float = 0.55
    active_salience: float = 0.35

    def __post_init__(self) -> None:
        for name, value in (
            ("speak_threshold", self.speak_threshold),
            ("impact_salience", self.impact_salience),
            ("excited_salience", self.excited_salience),
            ("active_salience", self.active_salience),
        ):
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")


class AudioEventDetector:
    def __init__(self, policy: AudioEventDetectionPolicy | None = None):
        self.policy = policy or AudioEventDetectionPolicy()

    def detect(self, audio: AudioFeatures | None) -> CommentaryEvent | None:
        if audio is None:
            return None
        if audio.event == "impact":
            return self._event(audio, "audio_impact", "Audio impact detected", self.policy.impact_salience)
        if audio.atmosphere == "excited":
            return self._event(audio, "audio_excited", "Audio became excited", self.policy.excited_salience)
        if audio.atmosphere == "active":
            return self._event(audio, "audio_active", "Audio became active", self.policy.active_salience)
        return None

    def _event(self, audio: AudioFeatures, kind: str, description: str, salience: float) -> CommentaryEvent:
        return CommentaryEvent(
            timestamp=audio.timestamp,
            kind=kind,
            description=description,
            salience=salience,
            should_speak=salience >= self.policy.speak_threshold,
            metadata={
                "source": "audio",
                "loudness": audio.loudness,
                "atmosphere": audio.atmosphere,
                "audio_event": audio.event,
                "rms": audio.rms,
                "peak": audio.peak,
            },
        )
