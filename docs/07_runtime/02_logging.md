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

## Usage

`PipelineStepResult.to_trace()` で step result から trace を作れる。

`RealtimePipeline.trace_step()` は `process_frame_step()` を実行し、queue state を含む trace を返す。

これにより、MVP では次を外部 logging library なしで確認できる。

- なぜ喋ったか。
- なぜ黙ったか。
- speech queue に入ったか。
- voice adapter まで到達したか。
