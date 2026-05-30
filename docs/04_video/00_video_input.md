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

## Adapter Boundary

OpenCV、ffmpeg、OBS capture は最終的に `Frame` を yield できればよい。core は decoder の種類を知らない。
