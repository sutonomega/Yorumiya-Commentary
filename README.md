# Yorumiya Commentary

## Overview

Yorumiya Commentary は、
動画内容を理解し、
自然なリアクションを返す
AI実況システムを作るプロジェクト。

単なる実況AIではなく、

「一緒に動画を見ている存在」

のような体験を目指している。

---

# Goals

このプロジェクトでは：

- 空気感
- 自然さ
- 存在感
- 発話タイミング

を重視する。

AIが常に喋り続けるのではなく、
必要な場面だけ、
短く自然に反応することを目標としている。

---

# Current MVP Scope

現在は、
最小構成（MVP）として：

- 動画入力
- フレーム解析
- 差分検出
- AIコメント生成
- 音声読み上げ

の成立を目指している。

---

# Planned Features

将来的には：

- リアルタイム実況
- OBS連携
- Whisper統合
- VAD
- 感情推定
- Companion Mode

なども検討している。

---

# Design Philosophy

## Natural Presence

実況量よりも、
場の空気を壊さないことを重視する。

---

## Small Local Models

ローカル環境で動作可能な、
小型LLM中心の構成を目指す。

---

## Modular Architecture

各責務を分離し、
拡張しやすい構造を維持する。

---

## Incremental Development

最初から巨大な構成を作らず、
小規模で成立させながら拡張していく。

---

# Project Structure

`````txt
00_overview/
01_requirements/
02_architecture/
03_ai/
04_video/
05_audio/
06_voice/
07_runtime/
08_experiments/
09_logs/
future_ideas/
`````

詳細な構成については：

- docs_structure.md

を参照。

---

# Documentation

## Overview

プロジェクト思想や方向性。

- project overview
- goals
- concepts
- design principles

---

## Requirements

必要機能やMVP範囲。

---

## Architecture

Pipeline や module構成。

---

## AI

人格設計やPrompt設計。

---

## Video / Audio / Voice

各技術領域。

---

## Runtime

scheduler や logging などの実行基盤。

- Local MVP runtime: `docs/07_runtime/05_local_mvp_runtime.md`

---

## Experiments

技術検証やPrompt検証。

---

# Current Status

現在は：

- ドキュメント設計
- architecture整理
- MVP定義

を進めている段階。

---

# Development Direction

まずは：

```txt
動画
↓
フレーム解析
↓
差分検出
↓
短いAIリアクション
↓
音声出力
```

という、
最小構成の成立を優先する。

その後：

- 音声解析
- 発話制御
- realtime化

などを段階的に追加していく予定。

---

# MP4 Commentary Smoke

OpenCV が入っている環境では、実際の mp4 を読み込んで既存 pipeline から comment まで流せる。

```bash
python3 -m pip install -e '.[video]'
```

```python
from yorumiya_commentary import run_mp4_commentary

results = run_mp4_commentary("sample.mp4", sample_interval_seconds=2.0, max_frames=5)
for result in results:
    if result.comment_decision.comment:
        print(result.comment_decision.comment.text)
```

sampled frame と comment decision を並べて確認したい場合は、review export を使う。

```python
from yorumiya_commentary import export_mp4_commentary_review

rows = export_mp4_commentary_review(
    "tests/fixtures/manual/Legacy.mp4",
    "tests/fixtures/manual/legacy_review",
    sample_interval_seconds=10.0,
    max_frames=5,
)
for row in rows:
    print(row["frame_path"], row["scene_summary"], row["comment"])
```

`review.jsonl` と sampled frame image が出力されるため、実際のシーンと comment を目視で確認できる。

内蔵の mp4 adapter は軽量な visual metadata だけを作る。ゲーム固有の理解を行う場合は、`vision_adapter` に vision model / OCR / object detector を接続する。

`vision_adapter` は `str` / `dict` / `SceneState` を返せる。`dict` の場合は `summary` / `labels` / `ui_elements` / `confidence` を返せる。最低限 `summary` または `labels` があれば scene analysis と comment generation に流せる。

```python
from yorumiya_commentary import run_mp4_commentary

def vision_adapter(frame):
    # imageをOCR/画像分類に渡し、その結果を返す想定
    return {
        "summary": "enemy battle",
        "labels": ["battle", "enemy"],
        "confidence": 0.9,
    }

results = run_mp4_commentary(
    "tests/fixtures/manual/Legacy.mp4",
    vision_adapter=vision_adapter,
    max_frames=2,
)
```

外部AI modelを接続する前の確認には、OpenCVだけで動く簡易adapterも使える。これは明るい高彩度エフェクトを `critical_moment` 候補として扱うbaselineで、キャラクター、敵、字幕の意味理解はしない。

```python
from yorumiya_commentary import OpenCVHeuristicVisionAdapter, run_mp4_commentary

results = run_mp4_commentary(
    "tests/fixtures/manual/Legacy.mp4",
    vision_adapter=OpenCVHeuristicVisionAdapter(),
    sample_interval_seconds=10.0,
    max_frames=5,
)
```

review log で確認する場合は `export_mp4_commentary_review(..., vision_adapter=OpenCVHeuristicVisionAdapter())` を使う。`review.jsonl` の `vision_adapter` に adapter 名が出る。

---

# Notes

このプロジェクトでは：

- 高テンション実況
- 常時喋り続けるAI
- 完全自動配信者

は目指していない。

「自然に一緒に見ている存在」

を重視する。
