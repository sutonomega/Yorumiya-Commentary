# Pipeline

Yorumiya Commentary は、動画と音声を小さな timestamp 付き状態へ変換し、意味のある変化が起きた時だけ短く反応する realtime commentary pipeline である。

基本方針は「まず黙る」。発話するには、event / audio / memory / timing のいずれかに明確な理由が必要になる。

## End-to-end Flow

```txt
Video / Audio source
  -> Frame / AudioChunk
  -> SceneState / Transcript / VadResult / AudioFeatures
  -> CommentaryEvent
  -> EmotionState
  -> CommentaryContext
  -> Comment
  -> SpeechItem
  -> SpeechAudio
```

## Processing Steps

1. `video` が timestamp 付き `Frame` を供給する。
2. `FrameSampler` が解析対象の frame を間引く。
3. `SceneAnalyzer` が frame を `SceneState` に変換する。
4. `EventDetector` が前回 scene と比較し、意味のある変化だけを `CommentaryEvent` にする。
5. `audio` module が `Transcript`、`VadResult`、`AudioFeatures` を補助情報として出す。
6. `EmotionEstimator` が人間の内面ではなく、場の盛り上がりと雰囲気を推定する。
7. `CommentaryContext` が scene、event、audio、emotion、memory、mode を統合する。
8. `CommentGenerator` が発話するか判断し、短い `Comment` を生成する。
9. `TaskQueue` が `SpeechItem` として発話候補を保持する。
10. `VoicevoxSynthesizer` などの voice adapter が音声化する。

## Pipeline Rules

- 沈黙は正常な出力である。
- すべての観測値は timestamp を持つ。
- core module は dataclass を受け渡し、外部 adapter の raw payload を漏らさない。
- adapter 失敗時は pipeline 全体を止めず、空結果または skip として扱う。
- 人が話している時は AI commentary を抑制する。ただし高 salience event は例外として扱える。

## MVP Boundary

MVP pipeline の目的は、すべてのモデル品質を解決することではない。まず次の流れが安全に成立することを確認する。

- frame input が scene state になる。
- scene state が event になる。
- audio signal が発話タイミングに影響する。
- comment が speech queue に入る。
- voice output を後から差し込める。

model quality、prompt tuning、OBS integration、長時間運用の安定性は、pipeline contract が固まってから扱う。
