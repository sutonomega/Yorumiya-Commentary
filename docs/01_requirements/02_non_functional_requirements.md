# Non-functional Requirements

## Responsiveness

realtime commentary では、完璧な解析より遅すぎない反応を優先する。

- frame sampling は predictable interval にする。
- 古くなった comment は無理に喋らない。
- speech queue は stale item を捨てられる設計にする。

## Reliability

外部 adapter は失敗する前提にする。

- model timeout は pipeline 全体を止めない。
- audio / video が欠けても context は作れる。
- voice engine が落ちても text comment は保持できる。

## Maintainability

module boundary を小さく保つ。

- core は外部 service に直接依存しない。
- adapter payload を core dataclass に変換する。
- tests は deterministic core を対象にする。

## Observability

後から判断を追えるようにする。

- timestamp を保持する。
- event salience を保持する。
- suppression reason を追えるようにする。
- latency measurement を module ごとに残せるようにする。

## Portability

local model と remote model の両方を扱えるようにする。

- provider 固有 API は adapter に閉じ込める。
- OS 固有の audio / video 処理は core から分離する。
- default tests は network なしで動く。
