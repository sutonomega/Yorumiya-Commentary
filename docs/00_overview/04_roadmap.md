# Roadmap

Roadmap は milestone ごとに system の責務を広げる。

## M1: Documentation Foundation

- overview / requirements / architecture を整理する。
- project の目的、責務、境界を明確にする。
- docs と実装 skeleton の対応を作る。

## M2: Minimal Commentary Pipeline

- video frame input
- frame sampling
- scene analysis
- event detection
- comment generation
- speech queue
- VOICEVOX adapter boundary

M2 の目的は「frame から発話候補まで流れること」を確認すること。

## M3: Realtime Foundation

- RealtimeScheduler
- run_due_steps()
- RealtimeLoop
- RuntimeTick
- RuntimeTickResult
- PipelineTrace
- SpeechTrace
- RuntimeTickTrace
- RuntimeTraceRecorder
- JSONL export

M3 の目的は「リアルタイム実行と観測の基盤を構築すること」。

Status: complete.

## M4: Audio Understanding

- AudioAnalyzer
- VoiceActivityDetector
- WhisperTranscriber
- transcript suppression
- AudioEventDetector
- EventSelectionTrace
- event source tracking

M4 の目的は「音声情報を実況判断へ統合すること」。

Status: complete.

## M5: Companion AI

- long memory
- companion mode
- emotional atmosphere estimation
- conversation context
- memory-aware response

M5 の目的は「一緒に過ごしている存在感」を作ること。
