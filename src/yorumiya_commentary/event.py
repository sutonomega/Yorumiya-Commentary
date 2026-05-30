from __future__ import annotations

from .models import CommentaryEvent, SceneState


class EventDetector:
    def __init__(self, speak_threshold: float = 0.45):
        self.previous: SceneState | None = None
        self.speak_threshold = speak_threshold

    def detect(self, current: SceneState) -> CommentaryEvent | None:
        if self.previous is None:
            self.previous = current
            return CommentaryEvent(
                timestamp=current.timestamp,
                kind="scene_initial",
                description=current.summary,
                salience=0.5,
                should_speak=True,
                metadata={"labels": list(current.labels)},
            )

        previous_labels = set(self.previous.labels)
        current_labels = set(current.labels)
        added = sorted(current_labels - previous_labels)
        removed = sorted(previous_labels - current_labels)
        summary_changed = current.summary != self.previous.summary
        salience = min(1.0, (len(added) + len(removed)) / 8 + (0.2 if summary_changed else 0.0))
        self.previous = current

        if salience <= 0:
            return None

        return CommentaryEvent(
            timestamp=current.timestamp,
            kind="scene_change",
            description=f"Scene changed: +{', '.join(added[:4]) or 'none'} / -{', '.join(removed[:4]) or 'none'}",
            salience=salience,
            should_speak=salience >= self.speak_threshold,
            metadata={"added": added, "removed": removed},
        )
