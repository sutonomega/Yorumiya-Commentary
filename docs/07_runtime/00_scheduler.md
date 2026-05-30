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
