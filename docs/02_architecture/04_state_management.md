# State Management

状態は大きく三層に分ける。

- current context: 直近 frame、音声、event、emotion。
- short memory: 直近の発話と状況。繰り返し抑制に使う。
- long memory: 重要な会話や状況の要約。Companion mode で参照する。

module は共有 mutable state を直接触らず、dataclass の状態を受け渡す。
