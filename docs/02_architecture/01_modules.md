# Modules

module は技術単位ではなく責務単位で分ける。各 module は一つの判断を担当し、小さな typed boundary を公開する。

## Module Map

| Module | 責務 | Input | Output |
| --- | --- | --- | --- |
| `video` | 動画入力と frame sampling | raw frames / iterable payloads | `Frame` |
| `scene` | 現在の画面理解 | `Frame` | `SceneState` |
| `event` | 変化検出と発話価値判定 | previous/current `SceneState` | `CommentaryEvent` |
| `audio` | 音声認識、人声検出、音量・雰囲気特徴 | `AudioChunk` | `Transcript`, `VadResult`, `AudioFeatures` |
| `ai` | 発話判断、comment 生成、memory、suppression | `CommentaryContext` | `Comment` |
| `voice` | 音声合成境界 | `SpeechItem` | `SpeechAudio` |
| `runtime` | timing、queue、end-to-end orchestration | module outputs | queue state / side effects |

## Core vs Adapter

core module は deterministic で dependency-light に保つ。core の責務は data contract、fallback behavior、suppression logic、orchestration である。

adapter は外部 system を担当する。

- OpenCV / ffmpeg / OBS capture
- local / remote vision model
- faster-whisper などの ASR engine
- webrtcvad や neural VAD
- VOICEVOX などの speech engine
- OpenAI、Gemini、Qwen、local model などの LLM provider

adapter は失敗する、遅い、local service を要求する、という前提で扱う。core module はその詳細を他 module に漏らさない。

## Ownership Rules

- `scene` は現在見えているものを説明する。前回比較はしない。
- `event` は状態差分を扱う。最終 comment は生成しない。
- `audio` は音声 signal の事実を出す。人格判断はしない。
- `ai` は「喋るか」「何を喋るか」を決める。raw media analysis はしない。
- `voice` は準備済み text を話す。comment 内容を書き換えない。
- `runtime` は module を接続する。model 固有 logic は持たない。

## Future Placement Notes

`EmotionEstimator` は現在 comment priority と suppression に近いため `ai` 側にある。ただし、今後 audio / video perception として育つ場合は `audio.emotion` または shared `perception` module へ移す。その場合も output contract は `EmotionState` のまま保つ。

`CompanionMode` は軽量 skeleton として存在する。M5 Companion milestone が主作業になるまでは optional / future 扱いにする。
