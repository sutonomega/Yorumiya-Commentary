# MVP Scope

MVP の目的は、Yorumiya Commentary の最小 pipeline が成立することを確認することである。

MVP は「高品質な AI 実況」を完成させる段階ではない。まず module 間の data flow、発話抑制、queue、adapter boundary が崩れないことを確認する。

## In Scope

- timestamp 付き `Frame` を扱える。
- frame sampling interval を変更できる。
- frame から `SceneState` を作れる。
- 前回 scene と比較して `CommentaryEvent` を作れる。
- `CommentaryContext` に scene / event / audio / memory / mode を統合できる。
- 発話すべきでない時に抑制できる。
- `Comment` を短く生成できる。
- `SpeechItem` を queue に入れられる。
- voice adapter に発話 text を渡せる。
- core tests が外部 service なしで動く。

## Out of MVP

- OBS overlay。
- GUI。
- 実 model の精度最適化。
- 長時間配信での production 運用。
- semantic memory / embedding search。
- 高度な感情分類。
- full-duplex conversation。

## MVP Success

MVP は次の状態になれば成功とする。

```txt
Frame
  -> SceneState
  -> CommentaryEvent
  -> CommentaryContext
  -> Comment
  -> SpeechItem
```

この流れが tests で確認でき、外部 adapter を後から差し込めること。
