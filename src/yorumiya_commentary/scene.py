from __future__ import annotations

from collections.abc import Callable

from .models import Frame, SceneState


class SceneAnalyzer:
    """Turns frame payloads into a lightweight natural-language scene state."""

    def __init__(self, vision_adapter: Callable[[Frame], SceneState] | None = None):
        self.vision_adapter = vision_adapter

    def analyze(self, frame: Frame) -> SceneState:
        if self.vision_adapter:
            return self.vision_adapter(frame)

        text = str(frame.data)
        labels = tuple(word.strip(".,:;!?").lower() for word in text.split() if len(word) > 3)
        ui_elements = tuple(word for word in labels if word in {"menu", "score", "hp", "map", "dialog"})
        summary = text if text else f"Frame {frame.index} from {frame.source}"
        return SceneState(
            timestamp=frame.timestamp,
            summary=summary,
            ui_elements=ui_elements,
            labels=labels[:12],
            confidence=0.35 if labels else 0.1,
        )
