# Error Handling

外部 adapter の失敗は pipeline 全体を止めない。Whisper、Vision、VOICEVOX の失敗は空結果または queue 保留として扱い、ログに残す。

## Runtime Service

`RuntimeService` は `RealtimeLoop` を常時実行するための thin wrapper である。

- `start()`: running flag を立てる。
- `stop()`: graceful shutdown 用に running flag を落とす。
- `run()`: finite tick iterable を処理する。
- `run_forever()`: application layer が渡す tick source を処理する。
- `snapshot()`: running state、metrics、queue、trace 件数を返す。

サービスは sleep、thread、signal handler を直接持たない。それらは application layer で扱い、core は deterministic にテストできる状態を保つ。

## Metrics

`RuntimeMetrics` は tick 数、frame step 数、speech step 数、comment 数、suppression 数、synthesized 数、error 数を集計する。

まずは in-memory counter として持ち、Prometheus などの監視 backend は adapter として追加する。
