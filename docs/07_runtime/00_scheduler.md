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
