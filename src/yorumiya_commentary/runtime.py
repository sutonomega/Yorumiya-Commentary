from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from time import monotonic
from typing import Any

from .ai import CommentDecision, CommentGenerator, EmotionEstimator
from .audio import AudioAnalyzer, VoiceActivityDetector, WhisperTranscriber
from .event import EventDetector
from .models import AudioChunk, CommentaryContext, Frame, SpeechAudio, SpeechItem
from .scene import SceneAnalyzer
from .voice import SpeechStyle, SpeechSynthesizer, comment_to_speech_item


@dataclass(frozen=True)
class SpeechQueuePolicy:
    max_items: int = 20
    stale_after_seconds: float = 12.0

    def __post_init__(self) -> None:
        if self.max_items <= 0:
            raise ValueError("max_items must be positive")
        if self.stale_after_seconds <= 0:
            raise ValueError("stale_after_seconds must be positive")


class TaskQueue:
    def __init__(self, speech_policy: SpeechQueuePolicy | None = None):
        self.speech_policy = speech_policy or SpeechQueuePolicy()
        self.events: deque[Any] = deque()
        self.speech: deque[SpeechItem] = deque()

    def put_event(self, event: Any) -> None:
        self.events.append(event)

    def get_event(self) -> Any | None:
        return self.events.popleft() if self.events else None

    def put_speech(self, item: SpeechItem) -> None:
        while len(self.speech) >= self.speech_policy.max_items:
            self.speech.popleft()
        self.speech.append(item)

    def get_speech(self, now: float | None = None) -> SpeechItem | None:
        if now is not None:
            self.drop_stale_speech(now)
        return self.speech.popleft() if self.speech else None

    def drop_stale_speech(self, now: float) -> int:
        dropped = 0
        while self.speech and now - self.speech[0].timestamp > self.speech_policy.stale_after_seconds:
            self.speech.popleft()
            dropped += 1
        return dropped

    def state(self) -> dict[str, int]:
        return {"events": len(self.events), "speech": len(self.speech)}


@dataclass(frozen=True)
class PipelineStepResult:
    context: CommentaryContext
    comment_decision: CommentDecision
    speech_item: SpeechItem | None = None
    speech_audio: SpeechAudio | None = None

    def to_trace(self) -> "PipelineTrace":
        return PipelineTrace.from_step_result(self)


@dataclass(frozen=True)
class PipelineTrace:
    timestamp: float
    event_kind: str | None
    event_salience: float | None
    decision_reason: str
    suppressed: bool
    has_comment: bool
    has_speech_item: bool
    has_speech_audio: bool
    queue_speech_count: int | None = None

    @classmethod
    def from_step_result(cls, result: PipelineStepResult, queue_state: dict[str, int] | None = None) -> "PipelineTrace":
        event = result.context.event
        return cls(
            timestamp=result.context.timestamp,
            event_kind=event.kind if event else None,
            event_salience=event.salience if event else None,
            decision_reason=result.comment_decision.reason,
            suppressed=result.comment_decision.suppressed,
            has_comment=result.comment_decision.comment is not None,
            has_speech_item=result.speech_item is not None,
            has_speech_audio=result.speech_audio is not None,
            queue_speech_count=queue_state.get("speech") if queue_state else None,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "timestamp": self.timestamp,
            "event_kind": self.event_kind,
            "event_salience": self.event_salience,
            "decision_reason": self.decision_reason,
            "suppressed": self.suppressed,
            "has_comment": self.has_comment,
            "has_speech_item": self.has_speech_item,
            "has_speech_audio": self.has_speech_audio,
            "queue_speech_count": self.queue_speech_count,
        }


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
        speech_style: SpeechStyle | None = None,
        voice_synthesizer: SpeechSynthesizer | None = None,
    ):
        self.scene_analyzer = scene_analyzer or SceneAnalyzer()
        self.event_detector = event_detector or EventDetector()
        self.emotion_estimator = emotion_estimator or EmotionEstimator()
        self.comment_generator = comment_generator or CommentGenerator()
        self.audio_analyzer = audio_analyzer or AudioAnalyzer()
        self.vad = vad or VoiceActivityDetector()
        self.transcriber = transcriber or WhisperTranscriber()
        self.queue = queue or TaskQueue()
        self.speech_style = speech_style or SpeechStyle()
        self.voice_synthesizer = voice_synthesizer

    def process_frame(self, frame: Frame, audio: AudioChunk | None = None) -> CommentaryContext:
        return self.process_frame_step(frame, audio).context

    def process_frame_step(self, frame: Frame, audio: AudioChunk | None = None, synthesize: bool = False) -> PipelineStepResult:
        context = self.build_context(frame, audio)
        if context.event:
            self.queue.put_event(context.event)

        decision = self.comment_generator.evaluate(context)
        speech_item = None
        if decision.comment:
            speech_item = comment_to_speech_item(decision.comment, self.speech_style)
            self.queue.put_speech(speech_item)

        speech_audio = self.synthesize_next_speech(now=frame.timestamp) if synthesize else None
        return PipelineStepResult(
            context=context,
            comment_decision=decision,
            speech_item=speech_item,
            speech_audio=speech_audio,
        )

    def trace_step(self, frame: Frame, audio: AudioChunk | None = None, synthesize: bool = False) -> PipelineTrace:
        result = self.process_frame_step(frame, audio=audio, synthesize=synthesize)
        return PipelineTrace.from_step_result(result, queue_state=self.queue.state())

    def build_context(self, frame: Frame, audio: AudioChunk | None = None) -> CommentaryContext:
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
        return context

    def run_once(self, frame: Frame, on_speech: Callable[[SpeechItem], None] | None = None) -> CommentaryContext:
        context = self.process_frame(frame)
        speech = self.queue.get_speech()
        if speech and on_speech:
            on_speech(speech)
        return context

    def synthesize_next_speech(self, now: float | None = None) -> SpeechAudio | None:
        if self.voice_synthesizer is None:
            return None
        speech = self.queue.get_speech(now=now)
        if speech is None:
            return None
        return self.voice_synthesizer.synthesize(speech)
