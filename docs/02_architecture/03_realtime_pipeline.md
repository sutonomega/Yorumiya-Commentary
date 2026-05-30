# Realtime Pipeline

realtime pipeline は module 内部の model logic を持たない。責務は ordering、timing、fallback behavior、queue handoff である。

## Runtime Loop

```txt
while running:
  if frame is due:
    capture or sample frame
    analyze scene
    detect event

  if audio is available:
    transcribe speech
    detect human speech
    analyze volume and atmosphere

  assemble context
  estimate atmosphere
  decide comment
  enqueue speech if needed
  synthesize or play queued speech when speech timing is safe
```

## Scheduler Responsibilities

`RealtimeScheduler` は作業の実行タイミングを決める。

- frame sampling interval
- inference interval
- speech interval
- low-priority retry timing

scheduler は「何を喋るか」を決めない。

## Queue Responsibilities

`TaskQueue` は event と speech を分ける。

- event queue は解析結果を後続 consumer に渡す。
- speech queue は再生可能になるまで発話候補を保持する。

queue があることで、生成と再生の速度差を吸収できる。

## Timing Policy

default timing policy は安定性を優先する。

- predictable interval で frame を sample する。
- speech を重ねない。
- 人声が検出されている時は喋らない。
- 古くなった comment は遅れて喋らず捨てる。
- high-salience event は low-priority queued comment より優先する。

## Failure Policy

realtime behavior は graceful degradation を前提にする。

- video frame がない: その tick の scene / event 処理を skip する。
- audio chunk がない: transcript / VAD / audio features なしで継続する。
- ASR failure: empty transcript として扱う。
- VAD failure: confidence 不明なら conservative silence に倒す。
- voice failure: text を log に残し、runtime policy に従って drop または retry する。

## Current Implementation

現在の skeleton は `RealtimePipeline.process_frame()` と `run_once()` に集約している。これは tests で contract を検証するには十分で、将来的な async loop 実装の余地を残している。
