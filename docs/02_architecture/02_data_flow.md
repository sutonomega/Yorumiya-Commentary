# Data Flow

Data flow は docs、実装、tests を一致させるための契約である。canonical model は `src/yorumiya_commentary/models.py` に置く。

## Primary Objects

| Object | 意味 | Created by | Consumed by |
| --- | --- | --- | --- |
| `Frame` | timestamp 付きの sampled video frame | `VideoInput`, `FrameSampler` | `SceneAnalyzer` |
| `AudioChunk` | timestamp と sample rate を持つ音声 samples | audio adapter | `WhisperTranscriber`, `VoiceActivityDetector`, `AudioAnalyzer` |
| `SceneState` | 現在の画面状態、summary、labels | `SceneAnalyzer` | `EventDetector`, `CommentaryContext` |
| `Transcript` | 音声認識 text と time range | `WhisperTranscriber` | `CommentaryContext` |
| `VadResult` | 人が話しているか | `VoiceActivityDetector` | `CommentGenerator`, scheduler policy |
| `AudioFeatures` | 音量と雰囲気 cue | `AudioAnalyzer` | `EmotionEstimator` |
| `CommentaryEvent` | 意味のある変化と salience | `EventDetector` | `EmotionEstimator`, `CommentGenerator` |
| `EmotionState` | excitement、atmosphere、speak priority | `EmotionEstimator` | `CommentGenerator` |
| `CommentaryContext` | 発話判断に使う統合 context | `RealtimePipeline` | `CommentGenerator` |
| `Comment` | 最終 text candidate | `CommentGenerator` | `TaskQueue` |
| `SpeechItem` | voice parameter 付き発話 item | `TaskQueue` | voice adapter |
| `SpeechAudio` | 合成済み audio bytes | `VoicevoxSynthesizer` | playback adapter |

## Context Assembly

`CommentaryContext` は runtime boundary 付近で組み立てる。これは「ある瞬間に AI が見聞きしていたもの」を表すため、作成が軽く、不要なら破棄できるべきである。

必須 field:

- `timestamp`
- `mode`

任意 field:

- `scene`
- `event`
- `transcript`
- `vad`
- `audio`
- `emotion`
- `memory`

任意 field にすることで、ある model や adapter が使えない時でも pipeline を継続できる。

## Timestamp Rule

すべての observation は source timestamp を持つ。derived object は、その object を発生させた event の timestamp を保持する。

これにより後から次を確認できる。

- AI は何を見ていたか。
- AI は何を聞いていたか。
- 何が変化したか。
- なぜ喋ったか。
- なぜ黙ったか。

## Suppression Data

発話抑制は context から説明できる必要がある。

- `VadResult.is_speech` は通常 commentary を抑制する。
- `CommentaryEvent.should_speak` は低 salience の変化を抑制する。
- `MemoryStore.is_repeated()` は同じ言い回しの繰り返しを抑制する。
- `EmotionState.speak_priority` は低 priority comment の遅延判断に使う。

これにより Quiet AI の思想をコード上で強制できる。
