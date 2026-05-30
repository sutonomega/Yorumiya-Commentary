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
