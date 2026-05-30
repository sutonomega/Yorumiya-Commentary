# Conversation Rules

- commentary mode はイベント反応を優先する。
- companion mode はユーザー発話への応答を優先する。
- VAD が人声を検出している時は、重要 event 以外は発話しない。
- 発話は短く、場面の余白を残す。
- memory は自然に使い、説明的に出しすぎない。

## MVP Commentary Rules

- `ui_change` は UI の変化に短く触れる。
- `label_change` は画面要素の追加・消失に短く触れる。
- `scene_change` は流れの変化として扱う。
- salience が低い event は黙る。
- stale な context は喋らない。
- repeated comment は memory で抑制する。
