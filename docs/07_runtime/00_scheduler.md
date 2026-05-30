# Scheduler

scheduler は tick、frame、inference、speech の周期を管理する。`RealtimeScheduler.due()` が指定 interval を満たした処理だけを実行する。

## Pipeline Step

`RealtimePipeline.process_frame_step()` は 1 frame 分の処理結果を `PipelineStepResult` として返す。

含まれるもの:

- `context`: frame から組み立てた `CommentaryContext`
- `comment_decision`: 発話または抑制の判断
- `speech_item`: queue に入れた発話 item
- `speech_audio`: voice adapter まで実行した場合の音声結果

既存の `process_frame()` は context だけを返す簡易 API として残す。

## Speech Step

`RealtimePipeline.run_speech_step()` は speech queue から次の `SpeechItem` を取り出し、voice adapter に渡す。

戻り値は `SpeechStepResult` である。

- `speech_item`: 処理した発話 item
- `speech_audio`: voice adapter が返した音声
- `skipped_reason`: `no_voice_synthesizer` または `no_speech`

これにより、frame 処理と音声化処理を scheduler から別々に呼べる。

## Due Steps

`RealtimePipeline.run_due_steps()` は `RealtimeScheduler` の interval 判定を使い、必要な step だけを実行する。

- frame が due で `frame` が渡されている場合: `process_frame_step()` を実行する。
- speech が due の場合: `run_speech_step()` を実行する。
- どちらも due でなければ何も実行しない。

戻り値は `RuntimeTickResult` で、`frame_due`、`speech_due`、`frame_step`、`speech_step` を確認できる。

これは本格的な realtime loop ではなく、M3 で loop を組むための小さな bridge である。

## Loop Runner

`RealtimeLoop` は `RuntimeTick` の列を順に処理する軽量 runner である。

- `RuntimeTick`: timestamp と任意の `frame` / `audio` を持つ。
- `RealtimeLoop.step()`: 1 tick を `run_due_steps()` に渡す。
- `RealtimeLoop.run()`: tick 列を処理し、`RuntimeTickResult` の list を返す。
- `RealtimeLoop.run_recorded()`: tick 列を処理し、`RuntimeTraceRecorder` に trace を蓄積する。
- `RealtimeLoop.run_frames()`: frame timestamp を tick timestamp として扱う。

`RealtimeLoop` は sleep、thread、asyncio を持たない。実時間の待機や停止制御は M3 以降の adapter / application layer で扱う。

`run_recorded()` と `RuntimeTraceRecorder.to_jsonl()` を組み合わせることで、deterministic な tick 列から runtime 全体の観測ログを JSONL として外へ渡せる。
