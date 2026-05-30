# Project Overview

Yorumiya Commentary は、動画を一緒に見ている存在として、必要な場面だけ自然に反応する AI commentary system である。

目指すものは、高頻度に喋り続ける実況 AI ではない。画面、音声、会話、場の雰囲気を読み取り、空気を壊さない短い反応を返す companion-like commentary を目指す。

## Core Idea

```txt
動画を見る
  -> 状況を理解する
  -> 変化を検出する
  -> 喋るべきか判断する
  -> 短く自然に反応する
```

この project では「何を見たか」よりも「いつ喋らないか」を重要視する。

## Primary Users

- ゲーム動画や配信を見ながら、横にいるような AI commentary を使いたいユーザー。
- 常時会話ではなく、場面に応じた短い反応を求めるユーザー。
- ローカルまたは小規模 model を組み合わせて、拡張可能な commentary system を作りたい開発者。

## Product Shape

初期段階では library / runtime skeleton として実装する。GUI や OBS overlay は後続の integration として扱う。

最初に安定させる対象:

- video frame input
- scene analysis
- event detection
- comment generation
- speech queue
- voice output adapter

## Current Direction

まずは小さく動く pipeline を作る。その後、Whisper、VAD、VOICEVOX、Vision model、Companion mode を段階的に強化する。
