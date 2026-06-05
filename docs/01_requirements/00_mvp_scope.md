# MVP Scope

MVP の目的は、README に記載している最小構成を成立させることである。

MVP は「高品質な AI 実況」を完成させる段階ではない。ただし、次の5項目が一つの流れとして動くことを成功条件にする。

- 動画入力
- フレーム解析
- 差分検出
- AIコメント生成
- 音声読み上げ

## In Scope

- mp4 などの動画入力から timestamp 付き `Frame` を扱える。
- frame sampling interval を変更できる。
- frame から `SceneState` を作れる。
- 前回 scene と比較して `CommentaryEvent` を作れる。
- `CommentaryContext` に scene / event / audio / memory / mode を統合できる。
- 発話すべきでない時に抑制できる。
- `Comment` を短く生成できる。
- `SpeechItem` を queue に入れられる。
- voice adapter に発話 text を渡し、音声読み上げの境界まで流せる。
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
Video input
  -> Frame
  -> SceneState
  -> CommentaryEvent
  -> CommentaryContext
  -> Comment
  -> SpeechItem
  -> Voice adapter
```

この流れが tests と実 mp4 review で確認でき、外部 adapter を後から差し込めること。
