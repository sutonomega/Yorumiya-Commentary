from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from .models import Comment, CommentaryContext, EmotionState, now_timestamp


SUPPRESSION_VAD_SPEECH = "vad_speech"
SUPPRESSION_TRANSCRIPT_SPEECH = "transcript_speech"
SUPPRESSION_LOW_SALIENCE = "low_salience"
SUPPRESSION_REPEATED_COMMENT = "repeated_comment"
SUPPRESSION_STALE_CONTEXT = "stale_context"
SUPPRESSION_NO_SIGNAL = "no_signal"


EVENT_PHASE_COMMENT_VARIANTS = {
    "combat_start": ("戦闘が始まったね",),
    "enemy_appeared": ("敵が出てきたね",),
    "boss_appeared": ("ボスだ",),
    "combat_end": ("ひと段落ついたね",),
}


EVENT_KIND_COMMENT_VARIANTS = {
    "critical_moment": ("今のは大きいね",),
    "objective_update": ("目標が更新されたね",),
    "item_update": ("何か手に入ったね",),
}


CRITICAL_DETAIL_COMMENT_VARIANTS = {
    "explosion_effect": ("すごいエフェクト出たね",),
}


@dataclass(frozen=True)
class CommentPolicy:
    max_length: int = 42
    min_salience: float = 0.45
    vad_interrupt_salience: float = 0.8
    transcript_interrupt_confidence: float = 0.65
    transcript_interrupt_salience: float = 0.8
    stale_after_seconds: float = 8.0

    def __post_init__(self) -> None:
        if self.max_length <= 0:
            raise ValueError("max_length must be positive")
        for name, value in (
            ("min_salience", self.min_salience),
            ("vad_interrupt_salience", self.vad_interrupt_salience),
            ("transcript_interrupt_confidence", self.transcript_interrupt_confidence),
            ("transcript_interrupt_salience", self.transcript_interrupt_salience),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0.0 and 1.0")
        if self.stale_after_seconds <= 0:
            raise ValueError("stale_after_seconds must be positive")


@dataclass(frozen=True)
class CommentDecision:
    comment: Comment | None
    suppressed: bool
    reason: str


class MemoryStore:
    def __init__(self, short_limit: int = 20, long_limit: int = 200):
        self.short_memory: deque[str] = deque(maxlen=short_limit)
        self.long_memory: deque[str] = deque(maxlen=long_limit)

    def add(self, item: str, long_term: bool = False) -> None:
        normalized = " ".join(item.split())
        if not normalized:
            return
        self.short_memory.append(normalized)
        if long_term and normalized not in self.long_memory:
            self.long_memory.append(normalized)

    def recall(self, query: str = "", limit: int = 5) -> tuple[str, ...]:
        source = list(self.long_memory) + list(self.short_memory)
        if not query:
            return tuple(source[-limit:])
        terms = set(query.lower().split())
        ranked = [item for item in source if terms & set(item.lower().split())]
        return tuple((ranked or source)[-limit:])

    def summarize(self, limit: int = 5) -> str:
        items = self.recall(limit=limit)
        return " / ".join(items)

    def as_dict(self) -> dict[str, list[str]]:
        return {
            "short_memory": list(self.short_memory),
            "long_memory": list(self.long_memory),
        }

    def save_long_memory(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.as_dict()["long_memory"], ensure_ascii=False, indent=2), encoding="utf-8")

    def load_long_memory(self, path: str | Path) -> None:
        target = Path(path)
        if not target.exists():
            return
        payload = json.loads(target.read_text(encoding="utf-8"))
        items = payload.get("long_memory", []) if isinstance(payload, dict) else payload
        for item in items:
            self.add(str(item), long_term=True)

    def is_repeated(self, text: str, window: int = 6) -> bool:
        return text in list(self.short_memory)[-window:]


class EmotionEstimator:
    def estimate(self, context: CommentaryContext) -> EmotionState:
        excitement = 0.0
        if context.event:
            excitement += context.event.salience * 0.55
        if context.audio:
            excitement += min(0.35, context.audio.rms)
            if context.audio.event:
                excitement += 0.15
        if context.vad and context.vad.is_speech:
            excitement += min(0.2, context.vad.speech_ratio)

        excitement = max(0.0, min(1.0, excitement))
        hinted_emotion = self._event_emotion_hint(context)
        if hinted_emotion:
            emotion, atmosphere = hinted_emotion
        elif excitement >= 0.7:
            emotion = "excited"
            atmosphere = "high"
        elif excitement >= 0.35:
            emotion = "interested"
            atmosphere = "active"
        else:
            emotion = "calm"
            atmosphere = "quiet"
        speak_priority = excitement if not (context.vad and context.vad.is_speech) else excitement * 0.45
        return EmotionState(context.timestamp, excitement, emotion, atmosphere, speak_priority)

    def _event_emotion_hint(self, context: CommentaryContext) -> tuple[str, str] | None:
        event = context.event
        if not event or event.kind != "critical_moment":
            return None
        labels = self._metadata_labels(event.metadata)
        if {"danger", "damage", "hit"} & labels:
            return "danger", "tense"
        if {"explosion", "effect"} & labels:
            return "surprised", "flashy"
        return None

    def _metadata_labels(self, metadata: dict[str, object]) -> set[str]:
        labels: set[str] = set()
        for key in ("labels", "added"):
            value = metadata.get(key)
            if isinstance(value, list):
                labels.update(str(label) for label in value)
        return labels


class CommentGenerator:
    def __init__(self, memory: MemoryStore | None = None, max_length: int = 42, policy: CommentPolicy | None = None):
        self.memory = memory or MemoryStore()
        self.policy = policy or CommentPolicy(max_length=max_length)

    def evaluate(self, context: CommentaryContext) -> CommentDecision:
        suppression_reason = self._suppression_reason(context)
        if suppression_reason:
            return CommentDecision(comment=None, suppressed=True, reason=suppression_reason)

        template = self._template(context)
        if template is None:
            return CommentDecision(comment=None, suppressed=True, reason=SUPPRESSION_NO_SIGNAL)

        text, priority, reason = template
        text = self._trim(text)
        if self.memory.is_repeated(text):
            return CommentDecision(comment=None, suppressed=True, reason=SUPPRESSION_REPEATED_COMMENT)

        self.memory.add(text)
        return CommentDecision(comment=Comment(timestamp=context.timestamp, text=text, priority=priority, reason=reason), suppressed=False, reason=reason)

    def generate(self, context: CommentaryContext) -> Comment | None:
        return self.evaluate(context).comment

    def _suppression_reason(self, context: CommentaryContext) -> str | None:
        if context.event and context.timestamp - context.event.timestamp > self.policy.stale_after_seconds:
            return SUPPRESSION_STALE_CONTEXT
        if context.vad and context.vad.is_speech and (not context.event or context.event.salience < self.policy.vad_interrupt_salience):
            return SUPPRESSION_VAD_SPEECH
        if self._has_interrupting_transcript(context):
            return SUPPRESSION_TRANSCRIPT_SPEECH
        if context.event and (not context.event.should_speak or context.event.salience < self.policy.min_salience):
            return SUPPRESSION_LOW_SALIENCE
        return None

    def _has_interrupting_transcript(self, context: CommentaryContext) -> bool:
        transcript = context.transcript
        if not transcript or not transcript.text:
            return False
        if transcript.confidence < self.policy.transcript_interrupt_confidence:
            return False
        return not context.event or context.event.salience < self.policy.transcript_interrupt_salience

    def _template(self, context: CommentaryContext) -> tuple[str, float, str] | None:
        if context.event:
            base = self._event_comment(context)
            priority = context.emotion.speak_priority if context.emotion else context.event.salience
            return base, priority, context.event.kind

        if context.transcript and context.transcript.text:
            return f"今の流れ、{context.transcript.text[:20]}が効いてるね", 0.35, "transcript"

        return None

    def _event_comment(self, context: CommentaryContext) -> str:
        assert context.event is not None
        phase_comment = self._event_phase_comment(context.event.metadata.get("event_phase"))
        if phase_comment:
            return phase_comment

        emotion = context.emotion.emotion if context.emotion else "calm"
        if context.event.kind == "ui_change":
            ui_added = context.event.metadata.get("ui_added", [])
            ui_removed = context.event.metadata.get("ui_removed", [])
            target = ", ".join((ui_added or ui_removed)[:2]) if isinstance(ui_added or ui_removed, list) else ""
            return f"UIが動いたね。{target}" if target else "UIが少し変わったね"
        if context.event.kind == "label_change":
            added = context.event.metadata.get("added", [])
            target = ", ".join(added[:2]) if isinstance(added, list) and added else ""
            return f"画面に{target}が増えたね" if target else "画面の要素が変わったね"
        critical_detail_comment = self._critical_detail_comment(context.event.kind, context.event.metadata)
        if critical_detail_comment:
            return critical_detail_comment
        event_kind_comment = self._select_comment_variant(EVENT_KIND_COMMENT_VARIANTS.get(context.event.kind))
        if event_kind_comment:
            return event_kind_comment

        if emotion == "excited":
            return f"お、今かなり動いたね。{context.event.description}"
        if emotion == "interested":
            return f"流れが少し変わったね。{context.event.description}"
        return f"ここ、変化があったね。{context.event.description}"

    def _event_phase_comment(self, event_phase: object) -> str | None:
        if not isinstance(event_phase, str):
            return None
        return self._select_comment_variant(EVENT_PHASE_COMMENT_VARIANTS.get(event_phase))

    def _critical_detail_comment(self, kind: str, metadata: dict[str, object]) -> str | None:
        if kind != "critical_moment":
            return None
        labels = self._metadata_labels(metadata)
        if {"explosion", "effect"} & labels:
            return self._select_comment_variant(CRITICAL_DETAIL_COMMENT_VARIANTS["explosion_effect"])
        return None

    def _select_comment_variant(self, variants: tuple[str, ...] | None) -> str | None:
        if not variants:
            return None
        return variants[0]

    def _metadata_labels(self, metadata: dict[str, object]) -> set[str]:
        labels: set[str] = set()
        for key in ("labels", "added"):
            value = metadata.get(key)
            if isinstance(value, list):
                labels.update(str(label) for label in value)
        return labels

    def _trim(self, text: str) -> str:
        return text if len(text) <= self.policy.max_length else text[: self.policy.max_length - 1] + "…"


@dataclass
class ConversationTurn:
    timestamp: float
    user_text: str
    response_text: str
    emotion: str = "calm"

    def as_dict(self) -> dict[str, object]:
        return {
            "timestamp": self.timestamp,
            "user_text": self.user_text,
            "response_text": self.response_text,
            "emotion": self.emotion,
        }


@dataclass
class CompanionMode:
    memory: MemoryStore = field(default_factory=MemoryStore)
    active: bool = False
    conversation_limit: int = 20
    turns: deque[ConversationTurn] = field(init=False)
    emotion: EmotionState | None = None

    def __post_init__(self) -> None:
        self.turns = deque(maxlen=self.conversation_limit)

    def switch(self, active: bool) -> None:
        self.active = active

    def observe(self, context: CommentaryContext) -> EmotionState | None:
        self.emotion = context.emotion
        if context.event and context.event.salience >= 0.8:
            self.memory.add(context.event.description, long_term=True)
        return self.emotion

    def conversation_context(self, limit: int = 5) -> tuple[ConversationTurn, ...]:
        return tuple(list(self.turns)[-limit:])

    def as_dict(self) -> dict[str, object]:
        return {
            "active": self.active,
            "memory": self.memory.as_dict(),
            "turns": [turn.as_dict() for turn in self.turns],
            "emotion": self.emotion.emotion if self.emotion else None,
        }

    def respond(self, user_text: str, context: CommentaryContext | None = None) -> Comment:
        if context:
            self.observe(context)
        recalled = self.memory.recall(user_text, limit=2)
        prefix = "うん、" if self.active else "実況側から見ると、"
        memory_hint = f" 前にも {recalled[-1]} があったね。" if recalled else ""
        emotion_hint = f" 今は{self.emotion.emotion}寄り。" if self.emotion and self.emotion.emotion != "calm" else ""
        text = f"{prefix}{user_text[:28]}。{memory_hint}".strip()
        text = f"{text}{emotion_hint}".strip()
        self.memory.add(user_text, long_term=True)
        timestamp = context.timestamp if context else now_timestamp()
        emotion = self.emotion.emotion if self.emotion else "calm"
        priority = self.emotion.speak_priority if self.emotion else 0.5
        comment = Comment(timestamp=timestamp, text=text, priority=priority, reason="companion")
        self.turns.append(ConversationTurn(timestamp=timestamp, user_text=user_text, response_text=text, emotion=emotion))
        return comment
