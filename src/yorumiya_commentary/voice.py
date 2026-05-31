from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .models import Comment, SpeechAudio, SpeechItem


class SpeechSynthesizer(Protocol):
    def synthesize(self, item: SpeechItem) -> SpeechAudio:
        ...


class AudioPlayer(Protocol):
    def play(self, audio: SpeechAudio) -> None:
        ...


class VoiceSynthesisError(RuntimeError):
    pass


@dataclass(frozen=True)
class PlaybackResult:
    audio: SpeechAudio | None = None
    played: bool = False
    skipped_reason: str | None = None


@dataclass(frozen=True)
class SpeechStyle:
    speaker: int = 3
    speed_scale: float = 1.0
    volume_scale: float = 1.0

    def __post_init__(self) -> None:
        if self.speaker < 0:
            raise ValueError("speaker must be non-negative")
        if self.speed_scale <= 0:
            raise ValueError("speed_scale must be positive")
        if self.volume_scale < 0:
            raise ValueError("volume_scale must be non-negative")


def comment_to_speech_item(comment: Comment, style: SpeechStyle | None = None) -> SpeechItem:
    resolved = style or SpeechStyle()
    return SpeechItem(
        timestamp=comment.timestamp,
        text=comment.text,
        speaker=resolved.speaker,
        speed_scale=resolved.speed_scale,
        volume_scale=resolved.volume_scale,
    )


@dataclass
class VoicevoxClient:
    endpoint: str = "http://127.0.0.1:50021"
    timeout: float = 10.0

    def audio_query(self, text: str, speaker: int) -> dict:
        url = f"{self.endpoint}/audio_query?{urlencode({'text': text, 'speaker': speaker})}"
        with urlopen(Request(url, method="POST"), timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def synthesis(self, query: dict, speaker: int) -> bytes:
        url = f"{self.endpoint}/synthesis?{urlencode({'speaker': speaker})}"
        body = json.dumps(query).encode("utf-8")
        request = Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=self.timeout) as response:
            return response.read()


class VoicevoxSynthesizer:
    def __init__(self, client: VoicevoxClient | None = None):
        self.client = client or VoicevoxClient()

    def synthesize(self, item: SpeechItem) -> SpeechAudio:
        try:
            query = self.client.audio_query(item.text, item.speaker)
            query["speedScale"] = item.speed_scale
            query["volumeScale"] = item.volume_scale
            audio = self.client.synthesis(query, item.speaker)
            return SpeechAudio(timestamp=item.timestamp, text=item.text, audio=audio)
        except Exception as exc:  # pragma: no cover - exact network exceptions depend on adapter/runtime.
            raise VoiceSynthesisError(str(exc)) from exc


class FakeVoiceSynthesizer:
    """Deterministic synthesizer for tests and offline pipeline checks."""

    def __init__(self, audio_prefix: bytes = b"FAKE-WAV:"):
        self.audio_prefix = audio_prefix
        self.items: list[SpeechItem] = []

    def synthesize(self, item: SpeechItem) -> SpeechAudio:
        self.items.append(item)
        audio = self.audio_prefix + item.text.encode("utf-8")
        return SpeechAudio(timestamp=item.timestamp, text=item.text, audio=audio, format="fake-wav")


class FakeAudioPlayer:
    def __init__(self):
        self.audios: list[SpeechAudio] = []

    def play(self, audio: SpeechAudio) -> None:
        self.audios.append(audio)
