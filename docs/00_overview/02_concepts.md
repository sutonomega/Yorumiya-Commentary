# Core Concept

Yorumiya Commentary の中心概念は Quiet AI である。

Quiet AI は、常に話す AI ではない。状況を見て、必要なら短く反応し、不要なら黙る AI である。

## MVP Commentary Mode

動画や配信の event に反応する mode。MVP ではこの mode を主対象にする。

- scene change を見る。
- salience が高い event だけ拾う。
- VAD が人声を検出している時は抑制する。
- short memory で繰り返しを避ける。

## Future Companion Concept

将来的には、ユーザーとの関係性や記憶を扱う Companion Mode を追加する。

- ユーザー発話に応答する。
- long memory を参照する。
- 実況 mode と共存する。
- 高頻度雑談ではなく、自然に隣にいる感覚を優先する。

Companion Mode は M5 以降の主題として扱う。MVP では思想上の将来像に留める。

## Reaction Policy

発話する条件:

- scene に意味のある変化がある。
- audio から盛り上がりが推定できる。
- ユーザーが明示的に話しかけている。
- memory と関連する重要な文脈がある。

発話しない条件:

- 人が話している。
- 変化が小さい。
- 直近と同じ内容になる。
- 発話が遅すぎて context が古い。

## Design Sentence

Yorumiya は、動画を説明し続ける AI ではなく、場面の余白を残しながら一緒に見ている存在である。
