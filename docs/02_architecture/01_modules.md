# Modules

- `video`: 動画入力、frame 切り出し、timestamp 管理。
- `scene`: frame 内容の説明と UI 要素の抽出。
- `event`: scene 差分、イベント化、発話必要性判定。
- `audio`: Whisper、VAD、音量と環境音特徴の解析。
- `ai`: prompt 方針、comment generator、memory、companion mode、感情推定。
- `voice`: VOICEVOX 接続、音声生成、発話 item 変換。
- `runtime`: queue、scheduler、realtime pipeline、error boundary。
