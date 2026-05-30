# Memory Design

memory は short と long に分ける。

- short memory: 直近発話、直近 event、繰り返し抑制。
- long memory: ユーザーが覚えてほしいと言った情報、重要場面、好み。

検索はまず keyword matching で十分とし、後から embedding adapter を追加できる。
