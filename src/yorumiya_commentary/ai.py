from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from .models import Comment, CommentaryContext, EmotionState, now_timestamp


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
        if excitement >= 0.7:
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


class CommentGenerator:
    def __init__(self, memory: MemoryStore | None = None, max_length: int = 42):
        self.memory = memory or MemoryStore()
        self.max_length = max_length

    def generate(self, context: CommentaryContext) -> Comment | None:
        if context.vad and context.vad.is_speech and (not context.event or context.event.salience < 0.8):
            return None
        if context.event and not context.event.should_speak:
            return None

        emotion = context.emotion.emotion if context.emotion else "calm"
        if context.event:
            base = self._event_comment(context.event.description, emotion)
            priority = context.emotion.speak_priority if context.emotion else context.event.salience
            reason = context.event.kind
        elif context.transcript and context.transcript.text:
            base = f"今の流れ、{context.transcript.text[:20]}が効いてるね"
            priority = 0.35
            reason = "transcript"
        else:
            return None

        text = self._trim(base)
        if self.memory.is_repeated(text):
            return None
        self.memory.add(text)
        return Comment(timestamp=context.timestamp, text=text, priority=priority, reason=reason)

    def _event_comment(self, description: str, emotion: str) -> str:
        if emotion == "excited":
            return f"お、今かなり動いたね。{description}"
        if emotion == "interested":
            return f"流れが少し変わったね。{description}"
        return f"ここ、変化があったね。{description}"

    def _trim(self, text: str) -> str:
        return text if len(text) <= self.max_length else text[: self.max_length - 1] + "…"


@dataclass
class CompanionMode:
    memory: MemoryStore = field(default_factory=MemoryStore)
    active: bool = False

    def switch(self, active: bool) -> None:
        self.active = active

    def respond(self, user_text: str, context: CommentaryContext | None = None) -> Comment:
        recalled = self.memory.recall(user_text, limit=2)
        prefix = "うん、" if self.active else "実況側から見ると、"
        memory_hint = f" 前にも {recalled[-1]} があったね。" if recalled else ""
        text = f"{prefix}{user_text[:28]}。{memory_hint}".strip()
        self.memory.add(user_text, long_term=True)
        return Comment(timestamp=context.timestamp if context else now_timestamp(), text=text, priority=0.5, reason="companion")
