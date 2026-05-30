from __future__ import annotations

from collections.abc import Iterable, Iterator

from .models import Frame


class VideoInput:
    """Small frame source abstraction for mp4/file/OBS adapters."""

    def __init__(self, frames: Iterable[object], source: str = "video", fps: float = 30.0):
        self.frames = frames
        self.source = source
        self.fps = fps

    def iter_frames(self) -> Iterator[Frame]:
        frame_duration = 1.0 / self.fps if self.fps > 0 else 0.0
        for index, data in enumerate(self.frames):
            yield Frame(timestamp=index * frame_duration, index=index, data=data, source=self.source)


class FrameSampler:
    def __init__(self, interval_seconds: float = 2.0):
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        self.interval_seconds = interval_seconds

    def sample(self, frames: Iterable[Frame]) -> Iterator[Frame]:
        next_timestamp = 0.0
        for frame in frames:
            if frame.timestamp + 1e-9 >= next_timestamp:
                yield frame
                next_timestamp = frame.timestamp + self.interval_seconds
