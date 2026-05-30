# State Management

state は小さく、明示的で、timestamp 付きに保つ。realtime commentary の判断は後から説明できる必要があるため、隠れた global state は避ける。

## State Layers

| Layer | Lifetime | Owner | Purpose |
| --- | --- | --- | --- |
| current context | 1回の判断 | `RealtimePipeline` | 観測値を統合し、喋るか決める |
| previous scene | 直近の解析済み scene | `EventDetector` | scene change を検出する |
| short memory | 直近の数件 | `MemoryStore` | 繰り返し抑制と近傍 context |
| long memory | session を跨ぐ情報 | `MemoryStore` / persistence adapter | user preference と重要場面の recall |
| queues | 処理されるまで | `TaskQueue` | generation と playback を分離する |
| runtime clock | process 起動中 | `RealtimeScheduler` | interval を制御する |

## Immutability Preference

多くの data model は frozen dataclass にする。module は値を受け取り、新しい値を作って次へ渡す。

mutable state は history が責務に含まれる component に限定する。

- `EventDetector.previous`
- `MemoryStore.short_memory`
- `MemoryStore.long_memory`
- `TaskQueue.events`
- `TaskQueue.speech`
- `RealtimeScheduler.last_run`

## Memory Policy

short memory は behavior control のために使う。

- 同じ comment の繰り返しを避ける。
- 直近の scene / speech decision を保持する。
- comment generation に近傍 context を渡す。

long memory は companion behavior のために使う。

- user preference
- 明示的に覚えてほしいと言われた情報
- 繰り返し現れる topic
- 長い session の summary

long memory は Companion mode が主 milestone になるまでは optional とする。

## Persistence Policy

core は特定 database を前提にしない。persistence は adapter として追加する。

- 初期実験: JSONL
- local structured history: SQLite
- semantic recall: vector storage
- multi-device usage: external memory service

persistence を足しても in-memory contract は変えない。

## Debuggability

すべての発話は次の情報から追跡できるべきである。

- timestamp
- scene summary
- event kind / salience
- VAD result
- audio atmosphere
- memory match
- final suppression / speaking decision

comment が不自然だった場合、これらの field で原因を追える状態にする。
