from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import Frame


@dataclass(frozen=True)
class OpenCVHeuristicVisionConfig:
    dark_threshold: float = 45.0
    bright_threshold: float = 180.0
    effect_saturation_threshold: int = 80
    effect_value_threshold: int = 180
    effect_pixel_ratio: float = 0.08
    orange_pixel_ratio: float = 0.03

    def __post_init__(self) -> None:
        if self.dark_threshold < 0:
            raise ValueError("dark_threshold must be non-negative")
        if self.bright_threshold <= self.dark_threshold:
            raise ValueError("bright_threshold must be greater than dark_threshold")
        for name, value in (
            ("effect_saturation_threshold", self.effect_saturation_threshold),
            ("effect_value_threshold", self.effect_value_threshold),
        ):
            if not 0 <= value <= 255:
                raise ValueError(f"{name} must be between 0 and 255")
        for name, value in (("effect_pixel_ratio", self.effect_pixel_ratio), ("orange_pixel_ratio", self.orange_pixel_ratio)):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0.0 and 1.0")


class OpenCVHeuristicVisionAdapter:
    def __init__(self, config: OpenCVHeuristicVisionConfig | None = None):
        self.config = config or OpenCVHeuristicVisionConfig()

    def __call__(self, frame: Frame) -> dict[str, Any]:
        data = frame.data if isinstance(frame.data, dict) else {}
        image = data.get("image")
        brightness = self._brightness(data, image)
        width, height = self._dimensions(data, image)
        labels = self._base_labels(brightness, width, height)
        effect_ratio, orange_ratio = self._effect_ratios(image)

        if effect_ratio >= self.config.effect_pixel_ratio:
            labels.extend(["effect", "critical"])
        if orange_ratio >= self.config.orange_pixel_ratio:
            labels.extend(["explosion", "critical"])

        labels = self._dedupe(labels)
        summary = self._summary(labels, width, height)
        confidence = 0.65 if "critical" in labels else 0.45
        return {
            "timestamp": frame.timestamp,
            "summary": summary,
            "labels": labels,
            "confidence": confidence,
        }

    def _base_labels(self, brightness: float | None, width: int | None, height: int | None) -> list[str]:
        labels = ["video_frame"]
        if brightness is not None:
            if brightness <= self.config.dark_threshold:
                labels.append("dark_scene")
            elif brightness >= self.config.bright_threshold:
                labels.append("bright_scene")
            else:
                labels.append("neutral_scene")
        if width and height:
            labels.append("wide_frame" if width >= height else "tall_frame")
        return labels

    def _brightness(self, data: dict[str, Any], image: object) -> float | None:
        if data.get("mean_brightness") is not None:
            try:
                return float(data["mean_brightness"])
            except (TypeError, ValueError):
                return None
        if image is not None and hasattr(image, "mean"):
            try:
                return float(image.mean())
            except (TypeError, ValueError):
                return None
        return None

    def _dimensions(self, data: dict[str, Any], image: object) -> tuple[int | None, int | None]:
        width = self._coerce_int(data.get("width"))
        height = self._coerce_int(data.get("height"))
        shape = getattr(image, "shape", None)
        if shape is not None and len(shape) >= 2:
            height = height or self._coerce_int(shape[0])
            width = width or self._coerce_int(shape[1])
        return width, height

    def _effect_ratios(self, image: object) -> tuple[float, float]:
        if image is None:
            return 0.0, 0.0
        cv2 = self._load_cv2()
        try:
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            effect_mask = cv2.inRange(
                hsv,
                (0, self.config.effect_saturation_threshold, self.config.effect_value_threshold),
                (179, 255, 255),
            )
            orange_mask = cv2.inRange(
                hsv,
                (5, self.config.effect_saturation_threshold, self.config.effect_value_threshold),
                (30, 255, 255),
            )
        except Exception:
            return 0.0, 0.0
        return self._mask_ratio(effect_mask), self._mask_ratio(orange_mask)

    def _mask_ratio(self, mask: object) -> float:
        if not hasattr(mask, "mean"):
            return 0.0
        try:
            return max(0.0, min(1.0, float(mask.mean()) / 255.0))
        except (TypeError, ValueError):
            return 0.0

    def _summary(self, labels: list[str], width: int | None, height: int | None) -> str:
        size = f" {width}x{height}" if width and height else ""
        if "explosion" in labels:
            return f"explosion effect video frame{size}".strip()
        if "effect" in labels:
            return f"bright effect video frame{size}".strip()
        return f"{' '.join(labels[:3])} video frame{size}".strip()

    def _dedupe(self, labels: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for label in labels:
            if label in seen:
                continue
            normalized.append(label)
            seen.add(label)
        return normalized

    def _coerce_int(self, value: object) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _load_cv2(self):
        try:
            import cv2  # type: ignore
        except ImportError as exc:
            raise ImportError("OpenCVHeuristicVisionAdapter requires the optional 'opencv-python' package") from exc
        return cv2
