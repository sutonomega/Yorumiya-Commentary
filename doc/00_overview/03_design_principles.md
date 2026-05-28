# Design Principles

## このドキュメントについて

このドキュメントでは、
Yorumiya Commentary の
設計思想を整理する。

主に：

- システム設計方針
- module分離方針
- AI設計方針
- 開発方針
- 拡張方針

など、

「どのように設計するか」

を定義することを目的とする。

---

# 小規模構成を重視する

最初から巨大なシステムを作らず、
小規模で成立する構成を優先する。

まずは：

- 動画入力
- frame解析
- 差分検出
- コメント生成
- 音声出力

など、

最小構成（MVP）を成立させることを重視する。

---

# 段階的に拡張する

最初から：

- realtime化
- 音声理解
- 感情推定
- 長期memory

まで作り込まない。

まずはシンプルな構成を成立させ、
必要に応じて段階的に拡張する。

---

# module責務を分離する

各moduleは：

「何を担当するか」

を明確に分離する。

例えば：

- video_source
- scene_analyzer
- event_detector
- comment_generator

などを独立させる。

---

# Pipeline中心で設計する

このプロジェクトでは、
単体module性能よりも：

- Pipeline構造
- 処理Flow
- Context整理
- 発話制御

など、

システム全体設計を重視する。

---

# 小型LLM中心で設計する

巨大GPU前提ではなく：

- 小型LLM
- ローカル動作
- 軽量構成
- 低遅延

を重視する。

これは：

- 個人開発しやすさ
- 継続運用
- 拡張自由度

を重視しているためである。

---

# Local First を重視する

可能な限り：

- ローカル推論
- ローカル保存
- ローカル実行

を優先する。

クラウド依存を減らし、
自由度と継続性を重視する。

---

# Quiet AI を重視する

このプロジェクトでは：

「喋り続けるAI」

ではなく、

「必要な時だけ自然に反応するAI」

を目指す。

そのため：

- suppression
- 発話制御
- タイミング制御

を重要な設計要素として扱う。

---

# Context整理を重視する

AI性能だけに依存せず、

- 状況整理
- event抽出
- memory整理
- 発話必要性判定

など、

LLMへ渡す前段処理を重視する。

---

# few-shot中心で設計する

巨大Promptよりも：

- short prompt
- good examples
- bad examples
- few-shot

を中心とした構成を重視する。

---

# 実験しやすさを重視する

このプロジェクトでは：

- model比較
- Prompt比較
- Pipeline比較
- latency測定

などを継続的に行う。

そのため：

- module分離
- logging
- experiment管理

を重視する。

---

# 実装と思想を分離する

例えば：

- 「どんなAIを目指すか」
- 「どんな空気感を重視するか」

は overview 側へ書く。

一方：

- OpenCV
- Whisper
- VOICEVOX

などの実装詳細は、
各技術ドキュメントへ分離する。

---

# 抽象から具体へ整理する

ドキュメント構造は：

```txt
overview
↓
requirements
↓
architecture
↓
implementation
```

の順で整理する。

上位ほど：

- 思想
- 目的
- 概念

を扱い、

下位ほど：

- module
- runtime
- implementation

へ近づく構造を採用する。

---

# 完璧主義より継続を重視する

最初から完璧を目指さず、

- 小さく作る
- 動かす
- 試す
- 改善する

サイクルを重視する。

継続的に積み上げられる構造を優先する。

---

# 長期的な拡張を前提にする

将来的には：

- realtime実況
- audio understanding
- Companion mode
- emotion integration

などを追加予定である。

そのため、
後から拡張しやすい構造を重視する。