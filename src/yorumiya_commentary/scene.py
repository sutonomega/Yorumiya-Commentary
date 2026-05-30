from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import re
from typing import Any

from .models import Frame, SceneState


UI_KEYWORDS = {
    "dialog",
    "hp",
    "inventory",
    "map",
    "menu",
    "quest",
    "score",
    "status",
}


@dataclass(frozen=True)
class SceneAnalysisConfig:
    max_labels: int = 12
    min_label_length: int = 3
    fallback_confidence: float = 0.35
    empty_confidence: float = 0.1

    def __post_init__(self) -> None:
        if self.max_labels <= 0:
            raise ValueError("max_labels must be positive")
        if self.min_label_length <= 0:
            raise ValueError("min_label_length must be positive")
        for name, value in (("fallback_confidence", self.fallback_confidence), ("empty_confidence", self.empty_confidence)):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0.0 and 1.0")


class SceneAnalyzer:
    """Turns frame payloads into a lightweight natural-language scene state."""

    def __init__(
        self,
        vision_adapter: Callable[[Frame], SceneState | dict[str, Any] | str] | None = None,
        config: SceneAnalysisConfig | None = None,
    ):
        self.vision_adapter = vision_adapter
        self.config = config or SceneAnalysisConfig()

    def analyze(self, frame: Frame) -> SceneState:
        if self.vision_adapter:
            return self._coerce_adapter_result(frame, self.vision_adapter(frame))

        if isinstance(frame.data, dict):
            return self._from_mapping(frame, frame.data)

        if isinstance(frame.data, (list, tuple, set)):
            return self._from_mapping(frame, {"summary": " ".join(str(item) for item in frame.data), "labels": list(frame.data)})

        return self._from_text(frame, str(frame.data))

    def _coerce_adapter_result(self, frame: Frame, result: SceneState | dict[str, Any] | str) -> SceneState:
        if isinstance(result, SceneState):
            return result
        if isinstance(result, dict):
            return self._from_mapping(frame, result)
        return self._from_text(frame, str(result))

    def _from_mapping(self, frame: Frame, payload: dict[str, Any]) -> SceneState:
        summary = str(payload.get("summary") or payload.get("description") or payload.get("data") or "")
        labels = self._normalize_labels(payload.get("labels") or payload.get("objects") or summary)
        ui_elements = self._normalize_ui_elements(payload.get("ui_elements") or payload.get("ui") or labels)
        confidence = self._coerce_confidence(payload.get("confidence"), labels)
        return SceneState(
            timestamp=float(payload.get("timestamp", frame.timestamp)),
            summary=summary or f"Frame {frame.index} from {frame.source}",
            ui_elements=ui_elements,
            labels=labels,
            confidence=confidence,
        )

    def _from_text(self, frame: Frame, text: str) -> SceneState:
        labels = self._normalize_labels(text)
        ui_elements = self._normalize_ui_elements(labels)
        summary = text if text else f"Frame {frame.index} from {frame.source}"
        return SceneState(
            timestamp=frame.timestamp,
            summary=summary,
            ui_elements=ui_elements,
            labels=labels,
            confidence=self.config.fallback_confidence if labels else self.config.empty_confidence,
        )

    def _normalize_labels(self, value: object) -> tuple[str, ...]:
        if value is None:
            return ()
        if isinstance(value, str):
            tokens = re.findall(r"[\w-]+", value.lower())
        else:
            tokens = [str(item).lower() for item in value if str(item).strip()]

        normalized: list[str] = []
        seen: set[str] = set()
        for token in tokens:
            label = token.strip(".,:;!?").replace(" ", "_")
            if len(label) < self.config.min_label_length or label in seen:
                continue
            normalized.append(label)
            seen.add(label)
            if len(normalized) >= self.config.max_labels:
                break
        return tuple(normalized)

    def _normalize_ui_elements(self, value: object) -> tuple[str, ...]:
        if isinstance(value, str):
            tokens = re.findall(r"[\w-]+", value.lower())
        else:
            tokens = [str(item).lower().strip(".,:;!?") for item in value if str(item).strip()]

        normalized: list[str] = []
        seen: set[str] = set()
        for token in tokens:
            label = token.replace(" ", "_")
            if label not in UI_KEYWORDS or label in seen:
                continue
            normalized.append(label)
            seen.add(label)
        return tuple(normalized)

    def _coerce_confidence(self, value: object, labels: tuple[str, ...]) -> float:
        if value is None:
            return self.config.fallback_confidence if labels else self.config.empty_confidence
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            return self.config.fallback_confidence if labels else self.config.empty_confidence
        return max(0.0, min(1.0, confidence))
