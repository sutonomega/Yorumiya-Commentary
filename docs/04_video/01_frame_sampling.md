# Frame Sampling

frame sampling は解析負荷を制御するため、固定 interval を基本にする。初期値は 2 秒で、ゲームや画面変化が激しい場合は短くする。

## Sampling Policy

`FrameSamplingPolicy` は次を管理する。

- `interval_seconds`: 解析間隔。
- `start_timestamp`: sampling 開始時刻。
- `end_timestamp`: sampling 終了時刻。
- `max_frames`: 最大取得 frame 数。
- `dedupe_timestamps`: 同じ timestamp の重複抑制。

## Behavior

`FrameSampler` は `Frame` iterable を受け取り、policy に合う frame だけを yield する。

これは realtime / batch の両方で使える。realtime では interval を短めに、batch tests では `max_frames` や `end_timestamp` で範囲を絞る。
