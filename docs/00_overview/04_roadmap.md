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

Status: complete for MVP. Scene, audio, transcript events are unified in `CommentaryEvent`; event selection and audio-derived suppression are traceable.

## M5: Companion AI

- long memory
- companion mode
- emotional atmosphere estimation
- conversation context
- memory-aware response

M5 の目的は「一緒に過ごしている存在感」を作ること。

Status: foundation. Memory persistence, conversation turns, and emotion-aware responses exist; richer companion behavior is still future work.

## M6: Voice Integration

- VoicevoxSynthesizer
- VoicevoxClient
- Speech queue integration
- voice trace

M6 の目的は「実際の音声合成エンジンと接続すること」。

Status: foundation. VOICEVOX adapter boundary, fake voice, playback boundary, and failure handling exist; live engine validation and playback integration remain.

## M7: Production Runtime

- while running loop
- runtime service
- graceful shutdown
- runtime metrics
- file recorder
- monitoring

M7 の目的は「常時稼働可能な realtime runtime を完成させること」。

Status: foundation. RuntimeService, metrics, graceful stop, and file trace recording exist; long-running service operations and monitoring remain.
