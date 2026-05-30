# Speech Timing

発話タイミングは queue と scheduler で制御する。VAD が人声を検出している場合は基本的に待ち、重要度の高い event のみ短く反応する。

## Speech Queue

`TaskQueue` は speech queue を持つ。`SpeechQueuePolicy` は次を管理する。

- `max_items`: queue に保持する最大 speech item 数。
- `stale_after_seconds`: 古くなった speech item を捨てる期限。

queue が溢れる場合は古い item から落とす。古くなった comment を遅れて喋るより、黙る方を優先する。

## Comment to Speech

`comment_to_speech_item()` は `Comment` を `SpeechItem` に変換する。speaker、speed、volume は `SpeechStyle` で指定する。

この変換を明示することで、comment generation と voice synthesis の責務を分離する。
