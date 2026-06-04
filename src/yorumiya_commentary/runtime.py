from __future__ import annotations

import json
from collections import deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from time import monotonic
from typing import Any

from .ai import (
    SUPPRESSION_LOW_SALIENCE,
    SUPPRESSION_NO_SIGNAL,
    SUPPRESSION_REPEATED_COMMENT,
    SUPPRESSION_STALE_CONTEXT,
    SUPPRESSION_TRANSCRIPT_SPEECH,
    SUPPRESSION_VAD_SPEECH,
    CommentDecision,
    CommentGenerator,
    EmotionEstimator,
)
from .audio import AudioAnalyzer, AudioEventDetector, TranscriptEventDetector, VoiceActivityDetector, WhisperTranscriber
from .event import EventDetector
from .models import AudioChunk, CommentaryContext, CommentaryEvent, Frame, SpeechAudio, SpeechItem
from .scene import SceneAnalyzer
from .voice import AudioPlayer, PlaybackResult, SpeechStyle, SpeechSynthesizer, comment_to_speech_item


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
    event_selection: "EventSelectionTrace | None" = None

    def to_trace(self) -> "PipelineTrace":
        return PipelineTrace.from_step_result(self)


@dataclass(frozen=True)
class EventSelectionTrace:
    selected_kind: str | None
    selected_source: str | None
    reason: str
    scene_event_kind: str | None = None
    scene_event_salience: float | None = None
    audio_event_kind: str | None = None
    audio_event_salience: float | None = None
    transcript_event_kind: str | None = None
    transcript_event_salience: float | None = None

    @classmethod
    def from_events(
        cls,
        scene_event: CommentaryEvent | None,
        audio_event: CommentaryEvent | None,
        selected: CommentaryEvent | None,
        transcript_event: CommentaryEvent | None = None,
    ) -> "EventSelectionTrace":
        events = {"scene": scene_event, "audio": audio_event, "transcript": transcript_event}
        present_sources = [source for source, event in events.items() if event is not None]
        selected_source = selected.metadata.get("source", "scene") if selected else None

        if not present_sources:
            reason = "no_event"
        elif len(present_sources) == 1:
            reason = f"{present_sources[0]}_only"
        elif selected_source == "audio":
            reason = "audio_higher_salience"
        elif selected_source == "transcript":
            reason = "transcript_higher_salience"
        else:
            reason = "scene_higher_or_equal_salience"
        return cls(
            selected_kind=selected.kind if selected else None,
            selected_source=selected_source,
            reason=reason,
            scene_event_kind=scene_event.kind if scene_event else None,
            scene_event_salience=scene_event.salience if scene_event else None,
            audio_event_kind=audio_event.kind if audio_event else None,
            audio_event_salience=audio_event.salience if audio_event else None,
            transcript_event_kind=transcript_event.kind if transcript_event else None,
            transcript_event_salience=transcript_event.salience if transcript_event else None,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "selected_kind": self.selected_kind,
            "selected_source": self.selected_source,
            "reason": self.reason,
            "scene_event_kind": self.scene_event_kind,
            "scene_event_salience": self.scene_event_salience,
            "audio_event_kind": self.audio_event_kind,
            "audio_event_salience": self.audio_event_salience,
            "transcript_event_kind": self.transcript_event_kind,
            "transcript_event_salience": self.transcript_event_salience,
        }


@dataclass(frozen=True)
class AudioContextTrace:
    timestamp: float
    has_audio: bool
    audio_loudness: str | None = None
    audio_atmosphere: str | None = None
    audio_event: str | None = None
    audio_rms: float | None = None
    audio_peak: float | None = None
    vad_is_speech: bool | None = None
    vad_speech_ratio: float | None = None
    vad_reason: str | None = None
    vad_active_samples: int | None = None
    has_transcript: bool = False
    transcript_confidence: float | None = None

    @classmethod
    def from_context(cls, context: CommentaryContext) -> "AudioContextTrace":
        audio = context.audio
        vad = context.vad
        transcript = context.transcript
        return cls(
            timestamp=context.timestamp,
            has_audio=audio is not None,
            audio_loudness=audio.loudness if audio else None,
            audio_atmosphere=audio.atmosphere if audio else None,
            audio_event=audio.event if audio else None,
            audio_rms=audio.rms if audio else None,
            audio_peak=audio.peak if audio else None,
            vad_is_speech=vad.is_speech if vad else None,
            vad_speech_ratio=vad.speech_ratio if vad else None,
            vad_reason=vad.reason if vad else None,
            vad_active_samples=vad.active_samples if vad else None,
            has_transcript=bool(transcript and transcript.text),
            transcript_confidence=transcript.confidence if transcript else None,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "timestamp": self.timestamp,
            "has_audio": self.has_audio,
            "audio_loudness": self.audio_loudness,
            "audio_atmosphere": self.audio_atmosphere,
            "audio_event": self.audio_event,
            "audio_rms": self.audio_rms,
            "audio_peak": self.audio_peak,
            "vad_is_speech": self.vad_is_speech,
            "vad_speech_ratio": self.vad_speech_ratio,
            "vad_reason": self.vad_reason,
            "vad_active_samples": self.vad_active_samples,
            "has_transcript": self.has_transcript,
            "transcript_confidence": self.transcript_confidence,
        }


@dataclass(frozen=True)
class PipelineTrace:
    timestamp: float
    event_kind: str | None
    event_source: str | None
    scene_event_phase: str | None
    event_salience: float | None
    decision_reason: str
    decision_source: str
    suppressed: bool
    has_comment: bool
    has_speech_item: bool
    has_speech_audio: bool
    queue_speech_count: int | None = None
    audio_trace: AudioContextTrace | None = None
    event_selection: EventSelectionTrace | None = None

    @classmethod
    def from_step_result(cls, result: PipelineStepResult, queue_state: dict[str, int] | None = None) -> "PipelineTrace":
        event = result.context.event
        return cls(
            timestamp=result.context.timestamp,
            event_kind=event.kind if event else None,
            event_source=event.metadata.get("source", "scene") if event else None,
            scene_event_phase=_scene_event_phase(event),
            event_salience=event.salience if event else None,
            decision_reason=result.comment_decision.reason,
            decision_source=_decision_source(result.comment_decision.reason),
            suppressed=result.comment_decision.suppressed,
            has_comment=result.comment_decision.comment is not None,
            has_speech_item=result.speech_item is not None,
            has_speech_audio=result.speech_audio is not None,
            queue_speech_count=queue_state.get("speech") if queue_state else None,
            audio_trace=AudioContextTrace.from_context(result.context),
            event_selection=result.event_selection,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "timestamp": self.timestamp,
            "event_kind": self.event_kind,
            "event_source": self.event_source,
            "scene_event_phase": self.scene_event_phase,
            "event_salience": self.event_salience,
            "decision_reason": self.decision_reason,
            "decision_source": self.decision_source,
            "suppressed": self.suppressed,
            "has_comment": self.has_comment,
            "has_speech_item": self.has_speech_item,
            "has_speech_audio": self.has_speech_audio,
            "queue_speech_count": self.queue_speech_count,
            "audio_trace": self.audio_trace.as_dict() if self.audio_trace else None,
            "event_selection": self.event_selection.as_dict() if self.event_selection else None,
        }


@dataclass(frozen=True)
class SpeechStepResult:
    speech_item: SpeechItem | None = None
    speech_audio: SpeechAudio | None = None
    skipped_reason: str | None = None
    error: str | None = None

    @property
    def synthesized(self) -> bool:
        return self.speech_audio is not None


@dataclass(frozen=True)
class SpeechTrace:
    timestamp: float
    synthesized: bool
    skipped_reason: str | None
    error: str | None
    has_speech_item: bool
    has_speech_audio: bool
    speech_timestamp: float | None = None
    audio_format: str | None = None

    @classmethod
    def from_step_result(cls, result: SpeechStepResult, timestamp: float) -> "SpeechTrace":
        return cls(
            timestamp=timestamp,
            synthesized=result.synthesized,
            skipped_reason=result.skipped_reason,
            error=result.error,
            has_speech_item=result.speech_item is not None,
            has_speech_audio=result.speech_audio is not None,
            speech_timestamp=result.speech_item.timestamp if result.speech_item else None,
            audio_format=result.speech_audio.format if result.speech_audio else None,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "timestamp": self.timestamp,
            "synthesized": self.synthesized,
            "skipped_reason": self.skipped_reason,
            "error": self.error,
            "has_speech_item": self.has_speech_item,
            "has_speech_audio": self.has_speech_audio,
            "speech_timestamp": self.speech_timestamp,
            "audio_format": self.audio_format,
        }


@dataclass(frozen=True)
class RuntimeTickResult:
    timestamp: float
    frame_due: bool
    speech_due: bool
    frame_step: PipelineStepResult | None = None
    speech_step: SpeechStepResult | None = None

    @property
    def traces(self) -> tuple[PipelineTrace, ...]:
        if self.frame_step is None:
            return ()
        return (self.frame_step.to_trace(),)

    def to_trace(self) -> "RuntimeTickTrace":
        return RuntimeTickTrace.from_tick_result(self)


@dataclass(frozen=True)
class RuntimeTickTrace:
    timestamp: float
    frame_due: bool
    speech_due: bool
    frame_trace: PipelineTrace | None = None
    speech_trace: SpeechTrace | None = None

    @classmethod
    def from_tick_result(cls, result: RuntimeTickResult) -> "RuntimeTickTrace":
        return cls(
            timestamp=result.timestamp,
            frame_due=result.frame_due,
            speech_due=result.speech_due,
            frame_trace=result.frame_step.to_trace() if result.frame_step else None,
            speech_trace=SpeechTrace.from_step_result(result.speech_step, result.timestamp) if result.speech_step else None,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "timestamp": self.timestamp,
            "frame_due": self.frame_due,
            "speech_due": self.speech_due,
            "frame_trace": self.frame_trace.as_dict() if self.frame_trace else None,
            "speech_trace": self.speech_trace.as_dict() if self.speech_trace else None,
        }


@dataclass
class RuntimeTraceRecorder:
    traces: list[RuntimeTickTrace] = field(default_factory=list)

    def record(self, result: RuntimeTickResult | RuntimeTickTrace) -> RuntimeTickTrace:
        trace = result if isinstance(result, RuntimeTickTrace) else result.to_trace()
        self.traces.append(trace)
        return trace

    def extend(self, results: Iterable[RuntimeTickResult | RuntimeTickTrace]) -> list[RuntimeTickTrace]:
        return [self.record(result) for result in results]

    def as_dicts(self) -> list[dict[str, object]]:
        return [trace.as_dict() for trace in self.traces]

    def to_jsonl(self) -> str:
        if not self.traces:
            return ""
        lines = [json.dumps(trace.as_dict(), ensure_ascii=False) for trace in self.traces]
        return "\n".join(lines) + "\n"


@dataclass
class RuntimeMetrics:
    ticks: int = 0
    frame_steps: int = 0
    speech_steps: int = 0
    comments: int = 0
    suppressions: int = 0
    synthesized: int = 0
    errors: int = 0

    def record(self, result: RuntimeTickResult) -> None:
        self.ticks += 1
        if result.frame_step:
            self.frame_steps += 1
            if result.frame_step.comment_decision.comment:
                self.comments += 1
            if result.frame_step.comment_decision.suppressed:
                self.suppressions += 1
        if result.speech_step:
            self.speech_steps += 1
            if result.speech_step.synthesized:
                self.synthesized += 1
            if result.speech_step.error:
                self.errors += 1

    def as_dict(self) -> dict[str, int]:
        return {
            "ticks": self.ticks,
            "frame_steps": self.frame_steps,
            "speech_steps": self.speech_steps,
            "comments": self.comments,
            "suppressions": self.suppressions,
            "synthesized": self.synthesized,
            "errors": self.errors,
        }


@dataclass(frozen=True)
class FileTraceRecorder:
    path: Path | str

    def write(self, traces: Iterable[RuntimeTickTrace]) -> int:
        rows = [json.dumps(trace.as_dict(), ensure_ascii=False) for trace in traces]
        if not rows:
            return 0
        target = Path(self.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as file:
            for row in rows:
                file.write(row + "\n")
        return len(rows)


@dataclass(frozen=True)
class RuntimeTick:
    timestamp: float
    frame: Frame | None = None
    audio: AudioChunk | None = None


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
        audio_event_detector: AudioEventDetector | None = None,
        transcript_event_detector: TranscriptEventDetector | None = None,
        vad: VoiceActivityDetector | None = None,
        transcriber: WhisperTranscriber | None = None,
        queue: TaskQueue | None = None,
        speech_style: SpeechStyle | None = None,
        voice_synthesizer: SpeechSynthesizer | None = None,
        audio_player: AudioPlayer | None = None,
    ):
        self.scene_analyzer = scene_analyzer or SceneAnalyzer()
        self.event_detector = event_detector or EventDetector()
        self.emotion_estimator = emotion_estimator or EmotionEstimator()
        self.comment_generator = comment_generator or CommentGenerator()
        self.audio_analyzer = audio_analyzer or AudioAnalyzer()
        self.audio_event_detector = audio_event_detector or AudioEventDetector()
        self.transcript_event_detector = transcript_event_detector or TranscriptEventDetector()
        self.vad = vad or VoiceActivityDetector()
        self.transcriber = transcriber or WhisperTranscriber()
        self.queue = queue or TaskQueue()
        self.speech_style = speech_style or SpeechStyle()
        self.voice_synthesizer = voice_synthesizer
        self.audio_player = audio_player

    def process_frame(self, frame: Frame, audio: AudioChunk | None = None) -> CommentaryContext:
        return self.process_frame_step(frame, audio).context

    def process_frame_step(self, frame: Frame, audio: AudioChunk | None = None, synthesize: bool = False) -> PipelineStepResult:
        context, event_selection = self.build_context_with_selection(frame, audio)
        if context.event:
            self.queue.put_event(context.event)

        decision = self.comment_generator.evaluate(context)
        speech_item = None
        if decision.comment:
            speech_item = comment_to_speech_item(decision.comment, self.speech_style)
            self.queue.put_speech(speech_item)

        speech_audio = self.run_speech_step(now=frame.timestamp).speech_audio if synthesize else None
        return PipelineStepResult(
            context=context,
            comment_decision=decision,
            speech_item=speech_item,
            speech_audio=speech_audio,
            event_selection=event_selection,
        )

    def trace_step(self, frame: Frame, audio: AudioChunk | None = None, synthesize: bool = False) -> PipelineTrace:
        result = self.process_frame_step(frame, audio=audio, synthesize=synthesize)
        return PipelineTrace.from_step_result(result, queue_state=self.queue.state())

    def run_due_steps(
        self,
        scheduler: RealtimeScheduler,
        *,
        frame: Frame | None = None,
        audio: AudioChunk | None = None,
        now: float | None = None,
    ) -> RuntimeTickResult:
        current = monotonic() if now is None else now
        frame_due = scheduler.due("frame", scheduler.frame_interval, now=current)
        speech_due = scheduler.due("speech", scheduler.speech_interval, now=current)

        frame_step = self.process_frame_step(frame, audio=audio) if frame_due and frame is not None else None
        speech_step = self.run_speech_step(now=current) if speech_due else None
        return RuntimeTickResult(
            timestamp=current,
            frame_due=frame_due,
            speech_due=speech_due,
            frame_step=frame_step,
            speech_step=speech_step,
        )

    def build_context(self, frame: Frame, audio: AudioChunk | None = None) -> CommentaryContext:
        return self.build_context_with_selection(frame, audio)[0]

    def build_context_with_selection(
        self,
        frame: Frame,
        audio: AudioChunk | None = None,
    ) -> tuple[CommentaryContext, EventSelectionTrace]:
        scene = self.scene_analyzer.analyze(frame)
        scene_event = self.event_detector.detect(scene)
        audio_features = self.audio_analyzer.analyze(audio) if audio else None
        audio_event = self.audio_event_detector.detect(audio_features)
        vad_result = self.vad.detect(audio) if audio else None
        transcript = self.transcriber.transcribe(audio) if audio else None
        transcript_event = self.transcript_event_detector.detect(transcript)
        event = self._select_event(scene_event, audio_event, transcript_event)
        event_selection = EventSelectionTrace.from_events(scene_event, audio_event, event, transcript_event)
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
        return context, event_selection

    def _select_event(
        self,
        scene_event: CommentaryEvent | None,
        audio_event: CommentaryEvent | None,
        transcript_event: CommentaryEvent | None = None,
    ) -> CommentaryEvent | None:
        selected = scene_event or audio_event or transcript_event
        for event in (audio_event, transcript_event):
            if event is not None and (selected is None or event.salience > selected.salience):
                selected = event
        return selected

    def run_once(self, frame: Frame, on_speech: Callable[[SpeechItem], None] | None = None) -> CommentaryContext:
        context = self.process_frame(frame)
        speech = self.queue.get_speech()
        if speech and on_speech:
            on_speech(speech)
        return context

    def synthesize_next_speech(self, now: float | None = None) -> SpeechAudio | None:
        return self.run_speech_step(now=now).speech_audio

    def run_speech_step(self, now: float | None = None) -> SpeechStepResult:
        if self.voice_synthesizer is None:
            return SpeechStepResult(skipped_reason="no_voice_synthesizer")
        speech = self.queue.get_speech(now=now)
        if speech is None:
            return SpeechStepResult(skipped_reason="no_speech")
        try:
            return SpeechStepResult(speech_item=speech, speech_audio=self.voice_synthesizer.synthesize(speech))
        except Exception as exc:
            return SpeechStepResult(speech_item=speech, skipped_reason="voice_synthesis_failed", error=str(exc))

    def run_playback_step(self, audio: SpeechAudio | None = None) -> PlaybackResult:
        if self.audio_player is None:
            return PlaybackResult(audio=audio, skipped_reason="no_audio_player")
        if audio is None:
            return PlaybackResult(skipped_reason="no_audio")
        self.audio_player.play(audio)
        return PlaybackResult(audio=audio, played=True)


@dataclass
class RealtimeLoop:
    pipeline: RealtimePipeline = field(default_factory=RealtimePipeline)
    scheduler: RealtimeScheduler = field(default_factory=RealtimeScheduler)

    def step(self, tick: RuntimeTick) -> RuntimeTickResult:
        return self.pipeline.run_due_steps(
            self.scheduler,
            frame=tick.frame,
            audio=tick.audio,
            now=tick.timestamp,
        )

    def run(self, ticks: Iterable[RuntimeTick]) -> list[RuntimeTickResult]:
        return [self.step(tick) for tick in ticks]

    def run_recorded(self, ticks: Iterable[RuntimeTick], recorder: RuntimeTraceRecorder | None = None) -> RuntimeTraceRecorder:
        resolved = recorder or RuntimeTraceRecorder()
        for tick in ticks:
            resolved.record(self.step(tick))
        return resolved

    def run_frames(self, frames: Iterable[Frame]) -> list[RuntimeTickResult]:
        return [self.step(RuntimeTick(timestamp=frame.timestamp, frame=frame)) for frame in frames]


@dataclass
class RuntimeService:
    loop: RealtimeLoop = field(default_factory=RealtimeLoop)
    recorder: RuntimeTraceRecorder = field(default_factory=RuntimeTraceRecorder)
    metrics: RuntimeMetrics = field(default_factory=RuntimeMetrics)
    file_recorder: FileTraceRecorder | None = None
    running: bool = False

    def start(self) -> None:
        self.running = True

    def stop(self) -> None:
        self.running = False

    @property
    def is_running(self) -> bool:
        return self.running

    def step(self, tick: RuntimeTick) -> RuntimeTickResult | None:
        if not self.running:
            return None
        result = self.loop.step(tick)
        trace = self.recorder.record(result)
        self.metrics.record(result)
        if self.file_recorder:
            self.file_recorder.write([trace])
        return result

    def run(
        self,
        ticks: Iterable[RuntimeTick],
        max_ticks: int | None = None,
        stop_when_done: bool = False,
    ) -> list[RuntimeTickResult]:
        self.start()
        results: list[RuntimeTickResult] = []
        try:
            for tick in ticks:
                if max_ticks is not None and len(results) >= max_ticks:
                    break
                result = self.step(tick)
                if result is None:
                    break
                results.append(result)
        finally:
            if stop_when_done:
                self.stop()
        return results

    def run_forever(
        self,
        tick_source: Iterable[RuntimeTick],
        max_ticks: int | None = None,
    ) -> list[RuntimeTickResult]:
        return self.run(tick_source, max_ticks=max_ticks, stop_when_done=False)

    def snapshot(self) -> dict[str, object]:
        return {
            "running": self.running,
            "metrics": self.metrics.as_dict(),
            "queue": self.loop.pipeline.queue.state(),
            "traces": len(self.recorder.traces),
            "file_recorder": str(self.file_recorder.path) if self.file_recorder else None,
        }


def _scene_event_phase(event: CommentaryEvent | None) -> str | None:
    if not event or event.metadata.get("source", "scene") != "scene":
        return None
    phase = event.metadata.get("event_phase")
    return phase if isinstance(phase, str) else None


def _decision_source(reason: str) -> str:
    if reason == SUPPRESSION_VAD_SPEECH:
        return "vad"
    if reason == SUPPRESSION_TRANSCRIPT_SPEECH:
        return "transcript"
    if reason in {SUPPRESSION_LOW_SALIENCE, SUPPRESSION_STALE_CONTEXT}:
        return "event"
    if reason == SUPPRESSION_REPEATED_COMMENT:
        return "memory"
    if reason == SUPPRESSION_NO_SIGNAL:
        return "none"
    return "event"
