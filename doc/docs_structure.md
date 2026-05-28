# ドキュメント構成説明

## このドキュメントについて

このドキュメントでは、
Yorumiya Commentary の
ドキュメント構成と役割を整理する。

主に：

- フォルダ構成
- ドキュメントの責務
- 抽象度の分離
- 設計思想

を定義する。

各ドキュメントの詳細内容ではなく、

「どこに何を書くべきか」

を整理することを目的とする。

---

# 全体構成

`````txt
README
↓
00_overview
↓
01_requirements
↓
02_architecture
↓
03_ai / 04_video / 05_audio ...
↓
07_runtime
↓
08_experiments
↓
09_logs
`````

---

# 構成の考え方

## 抽象から具体へ整理する

上位フォルダほど、
抽象度が高い内容を扱う。

下位フォルダほど、
実装や実験に近づく。

---

## 思想と実装を分離する

例えば：

- 「どんなAIを作りたいか」
- 「どんな空気感を目指すか」

などは、
overview に整理する。

一方：

- OpenCV
- Whisper
- VOICEVOX

などの実装技術は、
各技術フォルダへ分離する。

---

## Pipeline と Modules を分離する

Pipeline は：

「処理がどう流れるか」

を扱う。

Modules は：

「各moduleが何を担当するか」

を扱う。

---

## 実験と日次ログを分離する

experiments は：

- 技術検証
- Prompt検証
- モデル比較

などの知見を整理する。

logs は：

- 作業ログ
- 問題記録
- 日次記録

などを保存する。

---

# README.md

## 役割

プロジェクト全体の入口。

最初に読むことを想定する。

---

## 主な内容

- プロジェクト概要
- コンセプト
- ゴール
- MVP
- 現在の方向性
- フォルダ構成

---

# 00_overview/

## 役割

プロジェクト全体の思想を整理する。

このプロジェクトで：

- 何を作るか
- なぜ作るか
- 何を目指すか
- どんな価値観を重視するか

を定義する。

最も抽象度が高い層。

---

## 00_project_overview.md

プロジェクト概要。

「このプロジェクトは何か」

を整理する。

---

## 01_project_goal.md

最終的な目標や、
目指す体験を整理する。

---

## 02_concepts.md

コンセプト整理。

例えば：

- 一緒に見ている存在
- 空気感
- Companion的体験

など。

---

## 03_design_principles.md

設計思想。

例えば：

- 小型LLM中心
- シンプル構造
- 責務分離

など。

---

# 01_requirements/

## 役割

必要な機能や、
開発範囲を整理する。

「何が必要か」

を定義する層。

---

## 00_requirements.md

必要な機能要件を整理する。

---

## 01_mvp.md

最初に作る最小構成を整理する。

---

## 02_non_goals.md

やらないことを整理する。

---

## 03_future_features.md

将来的な機能案を整理する。

---

# 02_architecture/

## 役割

システム全体構造を整理する。

主に：

- 処理の流れ
- module分離
- 状態管理
- realtime構造

などを定義する。

---

## 00_pipeline.md

処理フローを整理する。

### 例

`````txt
動画入力
↓
フレーム供給
↓
映像解析
↓
差分検出
↓
コメント生成
`````

Pipeline は、
概念的な処理順を扱う。

---

## 01_modules.md

各moduleの責務を整理する。

### 例

- video_source
- video_analyzer
- event_detector

など。

Modules は、
実装責務を扱う。

---

## 02_data_flow.md

データの流れを整理する。

例えば：

- frame
- event
- context

など。

---

## 03_realtime_pipeline.md

リアルタイム実況時のFlowを整理する。

---

## 04_state_management.md

状態管理やmemory管理を整理する。

---

# 03_ai/

## 役割

AI人格や、
Prompt設計を整理する。

---

## 00_personality.md

AI人格仕様。

---

## 01_prompt_design.md

Prompt設計。

---

## 02_good_examples.md

良いfew-shot例。

---

## 03_bad_examples.md

悪いfew-shot例。

---

## 04_memory_design.md

memory設計。

---

## 05_conversation_rules.md

会話ルール。

---

# 04_video/

## 役割

映像処理関連を整理する。

---

## 00_video_input.md

動画入力。

---

## 01_frame_sampling.md

フレーム取得。

---

## 02_scene_analysis.md

映像解析。

---

## 03_event_detection.md

イベント検出。

---

## 04_vision_models.md

Visionモデル比較。

---

# 05_audio/

## 役割

音声処理関連を整理する。

---

## 00_audio_input.md

音声入力。

---

## 01_whisper.md

Whisper関連。

---

## 02_vad.md

人声検出。

---

## 03_audio_analysis.md

音声解析。

---

## 04_emotion_detection.md

感情推定。

---

# 06_voice/

## 役割

音声出力関連を整理する。

---

## 00_voicevox.md

VOICEVOX構成。

---

## 01_speech_timing.md

発話タイミング。

---

## 02_voice_styles.md

音声スタイル。

---

## 03_interrupt_control.md

割り込み制御。

---

# 07_runtime/

## 役割

実行基盤関連を整理する。

AI機能そのものではなく、
システム運用側を扱う。

---

## 00_scheduler.md

定期処理。

---

## 01_queue_system.md

Queue管理。

---

## 02_logging.md

ログ管理。

---

## 03_config_system.md

設定管理。

---

## 04_error_handling.md

エラー処理。

---

# 08_experiments/

## 役割

技術検証や、
実験結果を整理する。

知見蓄積を目的とする。

---

## 00_model_tests.md

モデル比較。

---

## 01_history_problem.md

history汚染問題。

---

## 02_fewshot_results.md

few-shot検証。

---

## 03_prompt_patterns.md

Promptパターン比較。

---

## 04_latency_tests.md

速度検証。

---

# 09_logs/

## 役割

日々の開発記録を保存する。

---

## daily_notes/

日次ログ。

---

## dev_logs/

開発記録。

---

## issue_notes/

問題記録。

---

# future_ideas/

## 役割

将来的なアイデアを保存する。

今は実装しないが、
将来的に検討したい内容を書く。

---

## 例

- companion_mode
- stream_mode
- emotion_memory
- multi_character

など。

---

# ファイル番号について

各フォルダでは：

`````txt
00_
01_
02_
`````

のように番号を付ける。

これは：

- 抽象 → 具体
- 上位 → 下位
- 思考順

で並べるため。

Obsidian上で、
自然な順番で閲覧できるようにすることを目的とする。