from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Any


def now_timestamp() -> float:
    return time()


@dataclass(frozen=True)
class Frame:
    timestamp: float
    index: int
    data: Any
    source: str = "unknown"


@dataclass(frozen=True)
class AudioChunk:
    timestamp: float
    samples: tuple[float, ...]
    sample_rate: int = 16000
    source: str = "unknown"


@dataclass(frozen=True)
class Transcript:
    timestamp: float
    text: str
    start: float
    end: float
    confidence: float = 0.0


@dataclass(frozen=True)
class VadResult:
    timestamp: float
    is_speech: bool
    speech_ratio: float
    start: float | None = None
    end: float | None = None


@dataclass(frozen=True)
class AudioFeatures:
    timestamp: float
    rms: float
    peak: float
    loudness: str
    atmosphere: str
    event: str | None = None


@dataclass(frozen=True)
class SceneState:
    timestamp: float
    summary: str
    ui_elements: tuple[str, ...] = ()
    labels: tuple[str, ...] = ()
    confidence: float = 0.0


@dataclass(frozen=True)
class CommentaryEvent:
    timestamp: float
    kind: str
    description: str
    salience: float
    should_speak: bool
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EmotionState:
    timestamp: float
    excitement: float
    emotion: str
    atmosphere: str
    speak_priority: float


@dataclass(frozen=True)
class CommentaryContext:
    timestamp: float
    scene: SceneState | None = None
    event: CommentaryEvent | None = None
    transcript: Transcript | None = None
    vad: VadResult | None = None
    audio: AudioFeatures | None = None
    emotion: EmotionState | None = None
    memory: tuple[str, ...] = ()
    mode: str = "commentary"


@dataclass(frozen=True)
class Comment:
    timestamp: float
    text: str
    priority: float
    reason: str


@dataclass(frozen=True)
class SpeechItem:
    timestamp: float
    text: str
    speaker: int = 3
    speed_scale: float = 1.0
    volume_scale: float = 1.0


@dataclass(frozen=True)
class SpeechAudio:
    timestamp: float
    text: str
    audio: bytes
    format: str = "wav"
