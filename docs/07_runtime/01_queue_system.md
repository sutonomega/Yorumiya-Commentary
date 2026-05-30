# Queue System

queue は event queue と speech queue に分ける。event は解析結果、speech は音声化対象として扱い、処理順を保つ。

## Step Result and Queue

`PipelineStepResult` により、queue に入った `SpeechItem` と voice adapter から返った `SpeechAudio` を同じ step で確認できる。

これにより、MVP では次の流れを外部 service なしで検証できる。

```txt
Frame
  -> CommentaryContext
  -> CommentDecision
  -> SpeechItem
  -> SpeechAudio
```

発話が抑制された場合は `speech_item` と `speech_audio` は `None` になり、`comment_decision.reason` に理由が残る。

## Speech Step Result

`SpeechStepResult` は speech queue から voice adapter へ渡す処理の結果を表す。

queue が空なら `skipped_reason = "no_speech"`、voice adapter が未設定なら `skipped_reason = "no_voice_synthesizer"` になる。

MVP では、音声化できなかった理由を例外ではなく step result として扱う。
