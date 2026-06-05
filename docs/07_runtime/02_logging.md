# Logging

ログは timestamp、module、event kind、latency、decision を記録する。後から latency 測定や問題分析に使える粒度にする。

## Pipeline Trace

`PipelineTrace` は本格的な logging backend ではなく、1 step の判断を記録する軽量 dataclass である。

記録するもの:

- `timestamp`
- `event_kind`
- `event_source`
- `scene_event_phase`
- `event_salience`
- `emotion`
- `emotion_atmosphere`
- `emotion_excitement`
- `decision_reason`
- `decision_source`
- `suppressed`
- `has_comment`
- `has_speech_item`
- `has_speech_audio`
- `queue_speech_count`
- `audio_trace`
- `event_selection`

`scene_event_phase` は scene event metadata の `event_phase` を記録する。`decision_reason=combat_state` と `scene_event_phase=combat_start` のように、大分類と小分類を分けて残すことで、phase comment が選ばれた理由を追いやすくする。

## Event Selection Trace

`EventSelectionTrace` は scene event、audio event、transcript event のどれを `CommentaryContext.event` に採用したかを記録する。

記録するもの:

- `selected_kind`
- `selected_source`
- `reason`
- `scene_event_kind`
- `scene_event_phase`
- `scene_event_salience`
- `audio_event_kind`
- `audio_event_salience`
- `transcript_event_kind`
- `transcript_event_salience`

`reason` は `scene_only`、`audio_only`、`transcript_only`、`audio_higher_salience`、`transcript_higher_salience`、`scene_higher_or_equal_salience`、`no_event` のいずれかである。

`scene_event_phase` は scene candidate の phase を記録する。`PipelineTrace.scene_event_phase` が採用後の phase を示すのに対し、`EventSelectionTrace.scene_event_phase` は選択前の scene 候補を確認するために使う。

## Decision Source

`PipelineTrace.decision_source` は最終判断の由来を記録する。

- `vad`: VAD による `vad_speech` suppression。
- `transcript`: transcript confidence による `transcript_speech` suppression。
- `event`: event kind、salience、stale context による判断。
- `memory`: repeated comment suppression。
- `none`: no signal。

これにより「音に反応した」のか、「音声情報によって黙った」のかを trace から分けて確認できる。

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
- `vad_reason`
- `vad_active_samples`
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

`FileTraceRecorder` は JSONL を file に append する最小 adapter である。directory 作成と追記だけを担当し、rotation や retention は application layer で扱う。

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
