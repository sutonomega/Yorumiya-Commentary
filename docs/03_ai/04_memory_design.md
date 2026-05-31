# Memory Design

memory は short と long に分ける。

- short memory: 直近発話、直近 event、繰り返し抑制。
- long memory: ユーザーが覚えてほしいと言った情報、重要場面、好み。

検索はまず keyword matching で十分とし、後から embedding adapter を追加できる。

## Persistence

`MemoryStore.save_long_memory()` は long memory を JSON として保存する。

`MemoryStore.load_long_memory()` は保存済み JSON を読み込み、既存の long memory に統合する。

`MemoryStore.as_dict()` は short / long memory の現在状態を返す。これは runtime snapshot や debug UI で使うための軽量な表現で、永続化の canonical schema ではない。

MVP では file path を受け取るだけに留める。SQLite、vector store、cloud sync は adapter / application layer で扱う。

## Summary

`MemoryStore.summarize()` は直近の memory を短い文字列にまとめる。これは prompt や companion response に渡すための軽量な入口であり、生成AIによる要約は後続 adapter で扱う。
