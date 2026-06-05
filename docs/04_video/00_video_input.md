# Video Input

動画入力は mp4、OBS、stream capture を将来 adapter として扱う。core は frame の iterable を受け取り、timestamp 付き `Frame` を生成する。

## Core Input

`VideoInput` は外部 decoder に依存しない。iterable payload と fps から `Frame` を生成する。

```txt
payload iterable
  -> VideoInput
  -> Frame(timestamp, index, data, source)
```

## File Fixture Input

`FrameFileInput` は tests / experiments 用の line-based input である。

- plain text line: そのまま frame data として扱う。
- JSON line: `data`、任意の `timestamp`、任意の `source` を読める。

これは mp4 decoder の代替ではなく、adapter contract を外部依存なしで検証するための入力である。

## MP4 File Input

`OpenCVVideoInput` は実際の mp4 file を読む optional adapter である。

```txt
mp4 file
  -> OpenCVVideoInput
  -> sampled Frame
  -> RealtimePipeline
  -> CommentDecision / SpeechItem
```

OpenCV (`cv2`) が利用できる環境では、動画を一定秒数ごとに読み、`Frame.data` に軽量な visual metadata を入れる。

- `summary`
- `labels`
- `confidence`
- `width`
- `height`
- `mean_brightness`

この metadata は「実 mp4 から pipeline を通して comment が出る」ことを確認するための最小情報である。高精度なゲーム状況理解はここでは行わない。

`export_mp4_commentary_review()` は sampled frame image と `review.jsonl` を出力する。これにより、実際のフレーム、scene summary、event、decision、comment を並べて確認できる。

ゲーム固有の理解を行う場合は、`SceneAnalyzer(vision_adapter=...)` に vision model / OCR / object detector を接続する。

大きな手動検証用 mp4 は `tests/fixtures/manual/` に置く。この directory は `.gitignore` で動画本体を Git 管理しない。

## Adapter Boundary

OpenCV、ffmpeg、OBS capture は最終的に `Frame` を yield できればよい。core は decoder の種類を知らない。
