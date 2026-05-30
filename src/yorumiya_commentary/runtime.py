from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from time import monotonic
from typing import Any

from .ai import CommentGenerator, EmotionEstimator
from .audio import AudioAnalyzer, VoiceActivityDetector, WhisperTranscriber
from .event import EventDetector
from .models import AudioChunk, CommentaryContext, Frame, SpeechItem
from .scene import SceneAnalyzer


class TaskQueue:
    def __init__(self):
        self.events: deque[Any] = deque()
        self.speech: deque[SpeechItem] = deque()

    def put_event(self, event: Any) -> None:
        self.events.append(event)

    def get_event(self) -> Any | None:
        return self.events.popleft() if self.events else None

    def put_speech(self, item: SpeechItem) -> None:
        self.speech.append(item)

    def get_speech(self) -> SpeechItem | None:
        return self.speech.popleft() if self.speech else None

    def state(self) -> dict[str, int]:
        return {"events": len(self.events), "speech": len(self.speech)}


@dataclass
class RealtimeScheduler:
    tick_interval: float = 0.2
    frame_interval: float = 2.0
    inference_interval: float = 2.0
    speech_interval: float = 3.0
    last_run: dict[str, float] = field(default_factory=dict)

    def due(self, name: str, interval: float | None = None, now: float | None = None) -> bool:
        current = monotonic() if now is None else now
        required = interval if interval is not None else self.tick_interval
        previous = self.last_run.get(name, float("-inf"))
        if current - previous >= required:
            self.last_run[name] = current
            return True
        return False


class RealtimePipeline:
    def __init__(
        self,
        scene_analyzer: SceneAnalyzer | None = None,
        event_detector: EventDetector | None = None,
        emotion_estimator: EmotionEstimator | None = None,
        comment_generator: CommentGenerator | None = None,
        audio_analyzer: AudioAnalyzer | None = None,
        vad: VoiceActivityDetector | None = None,
        transcriber: WhisperTranscriber | None = None,
        queue: TaskQueue | None = None,
    ):
        self.scene_analyzer = scene_analyzer or SceneAnalyzer()
        self.event_detector = event_detector or EventDetector()
        self.emotion_estimator = emotion_estimator or EmotionEstimator()
        self.comment_generator = comment_generator or CommentGenerator()
        self.audio_analyzer = audio_analyzer or AudioAnalyzer()
        self.vad = vad or VoiceActivityDetector()
        self.transcriber = transcriber or WhisperTranscriber()
        self.queue = queue or TaskQueue()

    def process_frame(self, frame: Frame, audio: AudioChunk | None = None) -> CommentaryContext:
        scene = self.scene_analyzer.analyze(frame)
        event = self.event_detector.detect(scene)
        audio_features = self.audio_analyzer.analyze(audio) if audio else None
        vad_result = self.vad.detect(audio) if audio else None
        transcript = self.transcriber.transcribe(audio) if audio else None
        context = CommentaryContext(
            timestamp=frame.timestamp,
            scene=scene,
            event=event,
            transcript=transcript,
            vad=vad_result,
            audio=audio_features,
        )
        emotion = self.emotion_estimator.estimate(context)
        memory = self.comment_generator.memory.recall(scene.summary)
        context = CommentaryContext(
            timestamp=frame.timestamp,
            scene=scene,
            event=event,
            transcript=transcript,
            vad=vad_result,
            audio=audio_features,
            emotion=emotion,
            memory=memory,
        )
        if event:
            self.queue.put_event(event)
        comment = self.comment_generator.generate(context)
        if comment:
            self.queue.put_speech(SpeechItem(timestamp=comment.timestamp, text=comment.text))
        return context

    def run_once(self, frame: Frame, on_speech: Callable[[SpeechItem], None] | None = None) -> CommentaryContext:
        context = self.process_frame(frame)
        speech = self.queue.get_speech()
        if speech and on_speech:
            on_speech(speech)
        return context
