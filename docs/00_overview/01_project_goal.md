# Project Goal

Yorumiya Commentary の goal は、動画や配信の空気感を壊さず、自然な存在感を持つ AI commentary を成立させることである。

## Product Goals

- 動画内の状況変化を検出できる。
- 必要な時だけ短く反応できる。
- 人が話している時は割り込まない。
- 同じ反応を繰り返さない。
- 音声出力まで接続できる。
- 外部 model や service を差し替えられる。

## Experience Goals

- 「一緒に見ている」感じを出す。
- 高テンション実況より、静かな存在感を優先する。
- 長文説明ではなく、短い自然な一言を返す。
- 沈黙を失敗扱いしない。
- ユーザーの発話や場面の余白を尊重する。

## Engineering Goals

- core と adapter を分離する。
- dataclass による明確な data flow を保つ。
- module ごとの責務を小さくする。
- 外部依存なしでも core tests が動く。
- 実 model の精度改善と runtime 構造を分けて進められる。

## Non-goals

- 完全自動の高頻度実況。
- 人間感情の正確な分類。
- 最初から全 model を本番品質で統合すること。
- GUI / overlay / OBS integration を MVP の必須条件にすること。
