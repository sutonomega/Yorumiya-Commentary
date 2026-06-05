from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from .models import Frame


@dataclass(frozen=True)
class FrameSamplingPolicy:
    interval_seconds: float = 2.0
    start_timestamp: float = 0.0
    end_timestamp: float | None = None
    max_frames: int | None = None
    dedupe_timestamps: bool = True

    def __post_init__(self) -> None:
        if self.interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        if self.start_timestamp < 0:
            raise ValueError("start_timestamp must be non-negative")
        if self.end_timestamp is not None and self.end_timestamp < self.start_timestamp:
            raise ValueError("end_timestamp must be greater than or equal to start_timestamp")
        if self.max_frames is not None and self.max_frames <= 0:
            raise ValueError("max_frames must be positive")


class VideoInput:
    """Small frame source abstraction for mp4/file/OBS adapters."""

    def __init__(self, frames: Iterable[object], source: str = "video", fps: float = 30.0):
        if fps <= 0:
            raise ValueError("fps must be positive")
        self.frames = frames
        self.source = source
        self.fps = fps

    def iter_frames(self) -> Iterator[Frame]:
        frame_duration = 1.0 / self.fps if self.fps > 0 else 0.0
        for index, data in enumerate(self.frames):
            yield Frame(timestamp=index * frame_duration, index=index, data=data, source=self.source)


class FrameFileInput:
    """Line-based frame fixture input for tests and simple adapters.

    Each non-empty line may be plain text payload or JSON with `data`,
    optional `timestamp`, and optional `source`.
    """

    def __init__(self, path: str | Path, source: str | None = None, fps: float = 30.0):
        if fps <= 0:
            raise ValueError("fps must be positive")
        self.path = Path(path)
        self.source = source or self.path.name
        self.fps = fps

    def iter_frames(self) -> Iterator[Frame]:
        frame_duration = 1.0 / self.fps
        with self.path.open("r", encoding="utf-8") as handle:
            index = 0
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                payload = self._parse_line(line)
                timestamp = payload.get("timestamp", index * frame_duration)
                source = payload.get("source", self.source)
                yield Frame(timestamp=float(timestamp), index=index, data=payload["data"], source=str(source))
                index += 1

    def _parse_line(self, line: str) -> dict[str, object]:
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            return {"data": line}
        if isinstance(parsed, dict):
            metadata = {key: parsed[key] for key in ("timestamp", "source") if key in parsed}
            return {"data": parsed.get("data", parsed), **metadata}
        return {"data": parsed}


class OpenCVVideoInput:
    """MP4 frame source backed by OpenCV.

    OpenCV is an optional dependency. The adapter emits lightweight visual
    metadata so a real video file can flow through the MVP pipeline without a
    vision model. Game-specific understanding should use a SceneAnalyzer
    vision_adapter.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        source: str | None = None,
        sample_interval_seconds: float = 2.0,
        start_timestamp: float = 0.0,
        end_timestamp: float | None = None,
        max_frames: int | None = None,
        fallback_fps: float = 30.0,
        include_image: bool = False,
    ):
        if sample_interval_seconds <= 0:
            raise ValueError("sample_interval_seconds must be positive")
        if start_timestamp < 0:
            raise ValueError("start_timestamp must be non-negative")
        if end_timestamp is not None and end_timestamp < start_timestamp:
            raise ValueError("end_timestamp must be greater than or equal to start_timestamp")
        if max_frames is not None and max_frames <= 0:
            raise ValueError("max_frames must be positive")
        if fallback_fps <= 0:
            raise ValueError("fallback_fps must be positive")
        self.path = Path(path)
        self.source = source or self.path.name
        self.sample_interval_seconds = sample_interval_seconds
        self.start_timestamp = start_timestamp
        self.end_timestamp = end_timestamp
        self.max_frames = max_frames
        self.fallback_fps = fallback_fps
        self.include_image = include_image

    def iter_frames(self) -> Iterator[Frame]:
        cv2 = self._load_cv2()
        capture = cv2.VideoCapture(str(self.path))
        if not capture.isOpened():
            raise ValueError(f"failed to open video file: {self.path}")

        try:
            fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0) or self.fallback_fps
            frame_duration = 1.0 / fps
            next_timestamp = self.start_timestamp
            emitted = 0
            frame_index = 0
            while True:
                ok, image = capture.read()
                if not ok:
                    break
                timestamp = frame_index * frame_duration
                frame_index += 1
                if self.end_timestamp is not None and timestamp > self.end_timestamp:
                    break
                if timestamp + 1e-9 < self.start_timestamp:
                    continue
                if timestamp + 1e-9 < next_timestamp:
                    continue

                yield Frame(
                    timestamp=timestamp,
                    index=frame_index - 1,
                    data=self._frame_data(image, timestamp),
                    source=self.source,
                )
                emitted += 1
                if self.max_frames is not None and emitted >= self.max_frames:
                    break
                next_timestamp = timestamp + self.sample_interval_seconds
        finally:
            capture.release()

    def _load_cv2(self):
        try:
            import cv2  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ImportError("OpenCVVideoInput requires the optional 'opencv-python' package") from exc
        return cv2

    def _frame_data(self, image: object, timestamp: float) -> dict[str, object]:
        height, width = self._shape(image)
        brightness = self._mean_brightness(image)
        brightness_label = self._brightness_label(brightness)
        aspect_label = self._aspect_label(width, height)
        labels = ["video_frame", brightness_label, aspect_label]
        data: dict[str, object] = {
            "summary": f"{brightness_label} video frame {width}x{height}",
            "labels": labels,
            "ui_elements": [],
            "confidence": 0.55,
            "timestamp": timestamp,
            "width": width,
            "height": height,
            "mean_brightness": round(brightness, 3),
        }
        if self.include_image:
            data["image"] = image
        return data

    def _shape(self, image: object) -> tuple[int, int]:
        shape = getattr(image, "shape", ())
        if len(shape) < 2:
            return 0, 0
        return int(shape[0]), int(shape[1])

    def _mean_brightness(self, image: object) -> float:
        mean = getattr(image, "mean", None)
        if callable(mean):
            return float(mean())
        return 0.0

    def _brightness_label(self, brightness: float) -> str:
        if brightness < 70:
            return "dark_scene"
        if brightness > 185:
            return "bright_scene"
        return "neutral_scene"

    def _aspect_label(self, width: int, height: int) -> str:
        if width <= 0 or height <= 0:
            return "unknown_frame"
        ratio = width / height
        if ratio >= 1.2:
            return "wide_frame"
        if ratio <= 0.8:
            return "tall_frame"
        return "square_frame"


class FrameSampler:
    def __init__(
        self,
        interval_seconds: float = 2.0,
        *,
        start_timestamp: float = 0.0,
        end_timestamp: float | None = None,
        max_frames: int | None = None,
        dedupe_timestamps: bool = True,
        policy: FrameSamplingPolicy | None = None,
    ):
        self.policy = policy or FrameSamplingPolicy(
            interval_seconds=interval_seconds,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            max_frames=max_frames,
            dedupe_timestamps=dedupe_timestamps,
        )

    def sample(self, frames: Iterable[Frame]) -> Iterator[Frame]:
        next_timestamp = self.policy.start_timestamp
        emitted = 0
        seen_timestamps: set[float] = set()
        for frame in frames:
            if self.policy.end_timestamp is not None and frame.timestamp > self.policy.end_timestamp:
                break
            if frame.timestamp + 1e-9 < self.policy.start_timestamp:
                continue
            if self.policy.dedupe_timestamps and frame.timestamp in seen_timestamps:
                continue
            if frame.timestamp + 1e-9 >= next_timestamp:
                yield frame
                emitted += 1
                seen_timestamps.add(frame.timestamp)
                if self.policy.max_frames is not None and emitted >= self.policy.max_frames:
                    break
                next_timestamp = frame.timestamp + self.policy.interval_seconds
