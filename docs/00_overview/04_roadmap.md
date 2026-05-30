# Roadmap

Roadmap は milestone ごとに system の責務を広げる。

## M1: Documentation Foundation

- overview / requirements / architecture を整理する。
- project の目的、責務、境界を明確にする。
- docs と実装 skeleton の対応を作る。

## M2: Minimal Commentary Pipeline

- video frame input
- frame sampling
- scene analysis
- event detection
- comment generation
- speech queue
- VOICEVOX adapter boundary

M2 の目的は「frame から発話候補まで流れること」を確認すること。

## M3: Audio Understanding

- Whisper integration
- VAD integration
- audio analyzer
- atmosphere estimation
- speech timing suppression

M3 の目的は「音声情報で喋る/黙る判断を改善すること」。

## M4: Runtime Stability

- realtime scheduler
- queue system
- logging
- error handling
- config system
- latency measurement

M4 の目的は「長く動かしても判断を追えること」。

## M5: Companion AI

- long memory
- companion mode
- emotional atmosphere estimation
- conversation context
- memory-aware response

M5 の目的は「一緒に過ごしている存在感」を作ること。
