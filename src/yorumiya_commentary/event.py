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
    semantic_event_bonus: float = 0.25

    def __post_init__(self) -> None:
        if not 0.0 <= self.speak_threshold <= 1.0:
            raise ValueError("speak_threshold must be between 0.0 and 1.0")
        if not 0.0 <= self.semantic_event_bonus <= 1.0:
            raise ValueError("semantic_event_bonus must be between 0.0 and 1.0")


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
        semantic_event = self._semantic_event(added, removed, ui_added, ui_removed, previous_labels, current_labels)
        event_phase = self._event_phase(semantic_event, added, previous_labels, current_labels)
        salience = self._salience(added, removed, ui_added, ui_removed, summary_changed, confidence_delta, semantic_event is not None)
        kind = semantic_event or self._kind(added, removed, ui_added, ui_removed, summary_changed)
        self.previous = current

        if salience <= 0:
            return None

        metadata = {
            "source": "scene",
            "added": added,
            "removed": removed,
            "ui_added": ui_added,
            "ui_removed": ui_removed,
            "summary_changed": summary_changed,
            "confidence_delta": confidence_delta,
            "semantic_event": semantic_event,
            "event_phase": event_phase,
        }
        if kind == "dialog_event":
            metadata.update(self._dialog_metadata(current))

        return CommentaryEvent(
            timestamp=current.timestamp,
            kind=kind,
            description=self._description(kind, added, removed, ui_added, ui_removed, current),
            salience=salience,
            should_speak=salience >= self.config.speak_threshold,
            metadata=metadata,
        )

    def _salience(
        self,
        added: list[str],
        removed: list[str],
        ui_added: list[str],
        ui_removed: list[str],
        summary_changed: bool,
        confidence_delta: float,
        has_semantic_event: bool = False,
    ) -> float:
        score = (len(added) + len(removed)) * self.config.label_weight
        score += (len(ui_added) + len(ui_removed)) * self.config.ui_weight
        score += self.config.summary_change_weight if summary_changed else 0.0
        score += confidence_delta * self.config.confidence_weight
        score += self.config.semantic_event_bonus if has_semantic_event else 0.0
        return min(1.0, score)

    def _semantic_event(
        self,
        added: list[str],
        removed: list[str],
        ui_added: list[str],
        ui_removed: list[str],
        previous_labels: set[str],
        current_labels: set[str],
    ) -> str | None:
        changed = set(added) | set(removed) | set(ui_added) | set(ui_removed)
        combat_labels = {"boss", "enemy", "battle", "combat"}
        if changed & combat_labels and (previous_labels | current_labels) & combat_labels:
            return "combat_state"
        if changed & {"critical", "damage", "hit", "ko", "death", "defeat", "danger"}:
            return "critical_moment"
        if changed & {"quest", "goal", "clear", "complete", "objective", "mission"}:
            return "objective_update"
        if changed & {"item", "loot", "inventory", "reward", "treasure"}:
            return "item_update"
        if changed & {"dialog", "subtitle", "choice"}:
            return "dialog_event"
        return None

    def _event_phase(
        self,
        semantic_event: str | None,
        added: list[str],
        previous_labels: set[str],
        current_labels: set[str],
    ) -> str | None:
        if semantic_event == "combat_state":
            return self._combat_event_phase(added, previous_labels, current_labels)
        if semantic_event == "dialog_event":
            return self._dialog_event_phase(added, previous_labels, current_labels)
        return None

    def _combat_event_phase(
        self,
        added: list[str],
        previous_labels: set[str],
        current_labels: set[str],
    ) -> str | None:
        added_labels = set(added)
        combat_labels = {"boss", "enemy", "battle", "combat"}
        previous_has_combat = bool(previous_labels & combat_labels)
        current_has_combat = bool(current_labels & combat_labels)

        if "boss" in added_labels:
            return "boss_appeared"
        if "enemy" in added_labels:
            return "enemy_appeared"
        if not previous_has_combat and current_has_combat:
            return "combat_start"
        if previous_has_combat and not current_has_combat:
            return "combat_end"
        return None

    def _dialog_event_phase(
        self,
        added: list[str],
        previous_labels: set[str],
        current_labels: set[str],
    ) -> str | None:
        added_labels = set(added)
        dialog_labels = {"dialog", "subtitle", "choice"}
        previous_has_dialog = bool(previous_labels & dialog_labels)
        current_has_dialog = bool(current_labels & dialog_labels)

        if "choice" in added_labels:
            return "dialog_choice"
        if not previous_has_dialog and current_has_dialog:
            return "dialog_start"
        if previous_has_dialog and not current_has_dialog:
            return "dialog_end"
        return None

    def _dialog_metadata(self, current: SceneState) -> dict[str, object]:
        metadata: dict[str, object] = {}
        for source_key, target_key in (("speaker", "dialog_speaker"), ("text", "dialog_text"), ("choice", "dialog_choice")):
            value = current.metadata.get(source_key)
            if value is not None:
                metadata[target_key] = value
        return metadata

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
        if kind == "combat_state":
            return f"Combat state changed: {current.summary}"
        if kind == "critical_moment":
            return f"Critical moment detected: {current.summary}"
        if kind == "objective_update":
            return f"Objective changed: {current.summary}"
        if kind == "item_update":
            return f"Item state changed: {current.summary}"
        if kind == "dialog_event":
            return f"Dialog state changed: {current.summary}"
        if kind == "ui_change":
            return f"UI changed: +{', '.join(ui_added[:4]) or 'none'} / -{', '.join(ui_removed[:4]) or 'none'}"
        if kind == "label_change":
            return f"Labels changed: +{', '.join(added[:4]) or 'none'} / -{', '.join(removed[:4]) or 'none'}"
        return f"Scene changed: {current.summary}"
