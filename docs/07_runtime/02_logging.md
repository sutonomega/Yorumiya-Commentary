# Logging

ログは timestamp、module、event kind、latency、decision を記録する。後から latency 測定や問題分析に使える粒度にする。

## Pipeline Trace

`PipelineTrace` は本格的な logging backend ではなく、1 step の判断を記録する軽量 dataclass である。

記録するもの:

- `timestamp`
- `event_kind`
- `event_salience`
- `decision_reason`
- `suppressed`
- `has_comment`
- `has_speech_item`
- `has_speech_audio`
- `queue_speech_count`
- `audio_trace`

## Audio Context Trace

`AudioContextTrace` は `CommentaryContext` に含まれる audio / VAD / transcript の状態を記録する。

記録するもの:

- `timestamp`
- `has_audio`
- `audio_loudness`
- `audio_atmosphere`
- `audio_event`
- `audio_rms`
- `audio_peak`
- `vad_is_speech`
- `vad_speech_ratio`
- `has_transcript`
- `transcript_confidence`

raw transcript text は recorder には入れない。会話内容の保存は後続の adapter / application layer で明示的に扱う。

## Speech Trace

`SpeechTrace` は `SpeechStepResult` から作る音声処理用の trace である。

記録するもの:

- `timestamp`
- `synthesized`
- `skipped_reason`
- `has_speech_item`
- `has_speech_audio`
- `speech_timestamp`
- `audio_format`

## Runtime Tick Trace

`RuntimeTickTrace` は 1 tick 全体の観測結果である。

記録するもの:

- `timestamp`
- `frame_due`
- `speech_due`
- `frame_trace`
- `speech_trace`

`frame_trace` は frame step が実行された場合だけ入る。`speech_trace` は speech step が実行された場合だけ入る。

## Trace Recorder

`RuntimeTraceRecorder` は `RuntimeTickResult` または `RuntimeTickTrace` を集める軽量 recorder である。

できること:

- `record()`: 1件の result / trace を保存する。
- `extend()`: result / trace の列を保存する。
- `as_dicts()`: 保存した trace を dict の list にする。
- `to_jsonl()`: 保存した trace を JSON Lines 文字列にする。

`RuntimeTraceRecorder` は保存先を持たない。file、SQLite、metrics backend への書き込みは adapter / application layer で扱う。

## Usage

`PipelineStepResult.to_trace()` で step result から trace を作れる。

`RealtimePipeline.trace_step()` は `process_frame_step()` を実行し、queue state を含む trace を返す。

`RuntimeTickResult.to_trace()` は `RuntimeTickResult` から `RuntimeTickTrace` を作る。

`RuntimeTraceRecorder.to_jsonl()` は trace を JSONL として外へ渡す最小の出口である。

これにより、MVP では次を外部 logging library なしで確認できる。

- なぜ喋ったか。
- なぜ黙ったか。
- speech queue に入ったか。
- voice adapter まで到達したか。
- tick ごとに frame / speech のどちらが動いたか。
