# Roadmap

Roadmap は milestone ごとに system の責務を広げる。

Current implementation status is summarized in `05_milestone_status.md`.

## Development Phases

### Phase 1: MVP Completion

目的は、ゲームの状況を検出し、自然な短文 comment を出し、なぜそうなったかを trace で追える状態にすること。

現在はこの phase にいる。

完了済み:

- `combat_state`
- `event_phase`
- `critical_moment`
- `objective_update`
- `item_update`
- phase comment
- kind comment
- repeated suppression
- `PipelineTrace`
- `EventSelectionTrace`

次にやる:

- `dialog_event` 設計を実装前に docs で整理する。
- `dialog_event` metadata として `speaker`、`text`、`choice` を検討する。
- `event_phase` を combat 以外へ拡張する。候補は `dialog_start`、`dialog_choice`、`dialog_end`。
- comment 選択ロジックを整理する。対象が増える場合は `_event_phase_comment()` と `_event_kind_comment()` の責務分割を検討する。

### Phase 2: Commentary Quality

目的は、状況を喋るだけでなく、少し感情を乗せた実況にすること。

今後やる:

- emotion を拡張する。現在の `calm` / `excited` を土台に、`surprised`、`danger`、`happy` などを検討する。
- comment の言い換えを追加する。例: `戦闘が始まったね`、`始まりそうだね`、`敵意を感じるね`。
- suppression を強化する。今は同文抑制が中心なので、似た意味、連続戦闘、会話ラッシュの抑制を検討する。

### Phase 3: AI Commentary

目的は、テンプレ実況から「夜宮灯らしい実況」へ進めること。

今後やる:

- speaker personality を設計する。
- 夜宮灯の口調を comment generation に反映する。
- 長期文脈を使う。例: `さっき苦戦してたね`。
- プレイスタイルを推定する。例: 慎重、探索好き、戦闘好き。
- `dialog_event` の `speaker` / `text` を活用して会話内容を実況へ反映する。

## Recommended Order

1. `dialog_event` 設計 docs
2. `dialog_event` phase 設計
3. emotion 拡張
4. comment 言い換え
5. suppression 強化
6. personality
7. 長期記憶

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
