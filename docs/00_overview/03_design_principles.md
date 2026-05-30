# Design Principles

## Natural Presence

AI が目立つことより、場の空気を壊さないことを優先する。

発話は短く、余白を残す。沈黙は failure ではなく、自然な選択肢である。

## Small Core

core は小さく保つ。外部 model、音声 engine、映像入力、保存先は adapter として差し替える。

core が守るもの:

- data model
- module boundary
- suppression rule
- queue / scheduler contract
- fallback behavior

## Adapter First

Whisper、VOICEVOX、Vision model、LLM provider は固定しない。OpenAI、Gemini、Qwen、SmolVLM、local model へ差し替えられる構造を保つ。

## Explainable Decisions

なぜ喋ったか、なぜ黙ったかを後から追えるようにする。

必要な trace:

- timestamp
- scene summary
- event salience
- VAD result
- audio atmosphere
- memory hit
- final decision

## Incremental Development

最初から大きな system を作らない。

1. docs と data model を揃える。
2. deterministic core を作る。
3. tests で contract を守る。
4. adapter を順番に接続する。
5. 実 data で threshold と prompt を調整する。
