from __future__ import annotations

from dataclasses import dataclass

from .models import CommentaryEvent, SceneState


@dataclass(frozen=True)
class EventDetectionConfig:
    speak_threshold: float = 0.45
    label_weight: float = 0.12
    ui_weight: float = 0.22
    summary_change_weight: float = 0.2
    confidence_weight: float = 0.15

    def __post_init__(self) -> None:
        if not 0.0 <= self.speak_threshold <= 1.0:
            raise ValueError("speak_threshold must be between 0.0 and 1.0")


class EventDetector:
    def __init__(self, speak_threshold: float = 0.45, config: EventDetectionConfig | None = None):
        self.previous: SceneState | None = None
        self.config = config or EventDetectionConfig(speak_threshold=speak_threshold)

    def detect(self, current: SceneState) -> CommentaryEvent | None:
        if self.previous is None:
            self.previous = current
            return CommentaryEvent(
                timestamp=current.timestamp,
                kind="scene_initial",
                description=current.summary,
                salience=max(0.35, min(0.7, current.confidence)),
                should_speak=True,
                metadata={"source": "scene", "labels": list(current.labels), "ui_elements": list(current.ui_elements)},
            )

        previous_labels = set(self.previous.labels)
        current_labels = set(current.labels)
        previous_ui = set(self.previous.ui_elements)
        current_ui = set(current.ui_elements)
        added = sorted(current_labels - previous_labels)
        removed = sorted(previous_labels - current_labels)
        ui_added = sorted(current_ui - previous_ui)
        ui_removed = sorted(previous_ui - current_ui)
        summary_changed = current.summary != self.previous.summary
        confidence_delta = max(0.0, current.confidence - self.previous.confidence)
        salience = self._salience(added, removed, ui_added, ui_removed, summary_changed, confidence_delta)
        kind = self._kind(added, removed, ui_added, ui_removed, summary_changed)
        self.previous = current

        if salience <= 0:
            return None

        return CommentaryEvent(
            timestamp=current.timestamp,
            kind=kind,
            description=self._description(kind, added, removed, ui_added, ui_removed, current),
            salience=salience,
            should_speak=salience >= self.config.speak_threshold,
            metadata={
                "source": "scene",
                "added": added,
                "removed": removed,
                "ui_added": ui_added,
                "ui_removed": ui_removed,
                "summary_changed": summary_changed,
                "confidence_delta": confidence_delta,
            },
        )

    def _salience(
        self,
        added: list[str],
        removed: list[str],
        ui_added: list[str],
        ui_removed: list[str],
        summary_changed: bool,
        confidence_delta: float,
    ) -> float:
        score = (len(added) + len(removed)) * self.config.label_weight
        score += (len(ui_added) + len(ui_removed)) * self.config.ui_weight
        score += self.config.summary_change_weight if summary_changed else 0.0
        score += confidence_delta * self.config.confidence_weight
        return min(1.0, score)

    def _kind(
        self,
        added: list[str],
        removed: list[str],
        ui_added: list[str],
        ui_removed: list[str],
        summary_changed: bool,
    ) -> str:
        if ui_added or ui_removed:
            return "ui_change"
        if added or removed:
            return "label_change"
        if summary_changed:
            return "scene_change"
        return "scene_stable"

    def _description(
        self,
        kind: str,
        added: list[str],
        removed: list[str],
        ui_added: list[str],
        ui_removed: list[str],
        current: SceneState,
    ) -> str:
        if kind == "ui_change":
            return f"UI changed: +{', '.join(ui_added[:4]) or 'none'} / -{', '.join(ui_removed[:4]) or 'none'}"
        if kind == "label_change":
            return f"Labels changed: +{', '.join(added[:4]) or 'none'} / -{', '.join(removed[:4]) or 'none'}"
        return f"Scene changed: {current.summary}"
