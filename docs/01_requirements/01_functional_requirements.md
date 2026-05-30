# Functional Requirements

## Video

- mp4 / stream / iterable frame source を adapter として扱える。
- frame に timestamp と index を付与できる。
- sampling interval に応じて解析 frame を選べる。
- 後続 module へ `Frame` を渡せる。

## Scene

- `Frame` から `SceneState` を生成できる。
- scene summary を保持できる。
- labels と UI elements を保持できる。
- vision model を adapter として差し替えられる。

## Event

- 前回 `SceneState` と現在 `SceneState` を比較できる。
- scene change を `CommentaryEvent` として表現できる。
- salience を計算できる。
- `should_speak` によって発話候補を制御できる。

## Audio

- `AudioChunk` を扱える。
- speech transcript を `Transcript` として扱える。
- VAD 結果を `VadResult` として扱える。
- rms / peak / atmosphere を `AudioFeatures` として扱える。

## AI Comment

- `CommentaryContext` を入力にできる。
- event と atmosphere に応じて短い comment を生成できる。
- VAD による発話抑制ができる。
- memory による繰り返し抑制ができる。

## Voice

- `SpeechItem` を voice adapter に渡せる。
- VOICEVOX HTTP API を呼ぶ boundary を持つ。
- speaker、speed、volume を指定できる。

## Runtime

- scheduler が処理 interval を管理できる。
- event queue と speech queue を分離できる。
- realtime pipeline が module を接続できる。
- adapter failure 時も core flow を止めない。
