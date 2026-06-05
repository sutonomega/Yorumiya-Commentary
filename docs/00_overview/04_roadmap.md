# Roadmap

Roadmap は milestone ごとに system の責務を広げる。

Current implementation status is summarized in `05_milestone_status.md`.

## Development Phases

### Phase 1: MVP Completion

目的は、README の最小構成である「動画入力、フレーム解析、差分検出、AIコメント生成、音声読み上げ」を一つの流れとして成立させること。

Status: complete for MVP scope.

確認済み:

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
- `dialog_event` design docs
- `dialog_event` phase detection
- 実 mp4 入力から sampled frame / `review.jsonl` までの確認
- MVP event detection acceptance cases
- Ollama comment adapter boundary
- `Comment -> SpeechItem -> voice adapter -> SpeechAudio` boundary

Phase 1 は高品質な実況の完成ではなく、README の最小構成が adapter contract と trace で説明可能に流れることを完了条件にする。実況品質、言い換え、長期文脈、personality は Phase 2 以降で扱う。

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

## PR Issue Roadmap

今後の作業は、1 PR = 1 Issue を基本単位にする。各 Issue には作業内容、ゴール、完了条件を明記し、PR は対応 Issue の完了条件だけを満たす小さな差分にする。

### Immediate Issues

1. Issue: [#77](https://github.com/sutonomega/Yorumiya-Commentary/issues/77) - `critical_moment` の detail comment を追加する。
   - 作業内容: `metadata.labels` / `metadata.added` の `explosion` / `effect` を見て、汎用 critical comment とは別の短文 comment を返す。
   - ゴール: OpenCV heuristic adapter で爆発/大きなエフェクトを検出した時に、「今のは大きいね」だけでなく見た目に合う短文 comment が出る。
   - 完了条件: 通常の `critical_moment` は従来コメントのまま、`explosion` / `effect` 付きの `critical_moment` だけ detail comment になるテストがある。

2. Issue: [#78](https://github.com/sutonomega/Yorumiya-Commentary/issues/78) - emotion を `critical_moment` の種類に合わせて拡張する。
   - 作業内容: 現在の `calm` / `interested` / `excited` を土台に、`surprised` / `danger` などの追加方針と最小実装を行う。
   - ゴール: 単に重要度が高いだけでなく、爆発、危険、ピンチなどの雰囲気を trace と comment 選択で扱えるようにする。
   - 完了条件: emotion trace に新しい emotion が出るケースと、既存ケースが壊れないテストがある。

3. Issue: [#81](https://github.com/sutonomega/Yorumiya-Commentary/issues/81) - comment variant map を追加する。
   - 作業内容: phase / kind / detail comment に複数候補を持てる構造を追加する。
   - ゴール: 同じ状況で常に同じ一文だけになる状態を緩和し、将来の口調調整へつなげる。
   - 完了条件: 既定動作が安定してテスト可能で、既存の repeated suppression と衝突しない。

4. Issue: [#80](https://github.com/sutonomega/Yorumiya-Commentary/issues/80) - suppression を意味単位で強化する。
   - 作業内容: 同文だけでなく、同じ event kind / detail group の連続発話を抑制する方針を追加する。
   - ゴール: `critical_moment` や爆発エフェクトが連続した時に、似た反応が並び続けるのを防ぐ。
   - 完了条件: 同文ではないが同じ意味の comment が連続した場合に抑制されるテストがある。

5. Issue: [#79](https://github.com/sutonomega/Yorumiya-Commentary/issues/79) - `dialog_event` metadata contract を実装へ進める。
   - 作業内容: `speaker` / `text` / `choice` を scene metadata として扱う最小contractを決め、trace に残す。
   - ゴール: 固定コメントを増やす前に、会話内容を使える土台を作る。
   - 完了条件: `dialog_event` の metadata が `PipelineTrace` / `EventSelectionTrace` で確認できるテストがある。

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
