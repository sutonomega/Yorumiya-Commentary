# Event Detection

EventDetector は「コメントを増やす場所」ではなく、「今の動画で反応する価値がある出来事を決める場所」として扱う。

基本入力は前回と現在の `SceneState` で、`labels`、`ui_elements`、`summary`、`confidence` の差分から `CommentaryEvent` を作る。後続の `CommentGenerator` は、ここで選ばれた event kind と metadata を使って短い反応を作る。

## Detection Priority

同じフレーム差分から複数の意味が読める場合は、次の順で event kind を決める。

1. semantic scene event
2. ui change
3. label change
4. summary-only scene change

semantic scene event は、単なる画面差分よりも「動画の流れとして意味がある」ものを優先して分類する。たとえば `battle` が増えた時は `label_change` ではなく `combat_state` として扱う。

## Scene Event Kinds

| kind | 検知条件 | 目的 |
| --- | --- | --- |
| `scene_initial` | 最初の scene | 初期状態を context に入れる |
| `combat_state` | `battle`、`enemy`、`boss`、`combat` など戦闘状態の label が追加/消失する | 戦闘開始、敵出現、ボス登場、戦闘終了などに反応する |
| `critical_moment` | `critical`、`damage`、`hit`、`ko`、`death`、`defeat`、`danger` などが追加/消失する | ダメージ、危機、決着などの瞬間を拾う |
| `objective_update` | `quest`、`goal`、`clear`、`complete`、`objective`、`mission` などが追加/消失する | 目標更新、クリア、ミッション進行を拾う |
| `item_update` | `item`、`loot`、`inventory`、`reward`、`treasure` などが追加/消失する | アイテム取得、報酬、インベントリ変化を拾う |
| `dialog_event` | `dialog`、`subtitle`、`choice` などが追加/消失する | 会話、字幕、選択肢表示を拾う |
| `ui_change` | UI element が追加/消失する | メニュー、HP、スコア、マップなど UI の変化を拾う |
| `label_change` | labels が追加/消失する | semantic rule に当たらない画面要素の変化を拾う |
| `scene_change` | labels/UI は同じだが summary が変わる | 流れの変化を弱く拾う |

`combat_state` は現在 scene だけでなく previous scene も見て判定する。これにより `battle enemy` から `field` に戻るような戦闘終了も取りこぼさない。

## Dialog Event Design

`dialog_event` は現時点では単一 kind にまとめる。ただし固定 comment はまだ持たせない。会話や字幕は連続しやすく、「会話が始まったね」のような固定文だけを入れると同じ反応が続きやすいためである。

RPG / ADV 対応を進める段階では、metadata に次の情報を入れることを検討する。

- `speaker`
- `text`
- `choice`

また、`event_phase` として次の分割を検討する。

- `dialog_start`
- `dialog_choice`
- `dialog_end`

連続検出時は repeated comment suppression だけに頼らず、同じ会話が継続している状態として扱うことも検討する。

MVP では `dialog_event` は trace と context には残すが、専用 comment は生成しない。

## Event Phase

`kind` は event の大分類を表す。`event_phase` は、その kind の中で「何を喋る価値があるか」を判断するための小分類として metadata に入れる。

MVP では `combat_state` だけ `event_phase` を持つ。

| kind | event_phase | 判定 |
| --- | --- | --- |
| `combat_state` | `combat_start` | previous に combat label がなく、current に `battle`、`combat`、`enemy`、`boss` のいずれかがある |
| `combat_state` | `combat_end` | previous に combat label があり、current に combat label がない |
| `combat_state` | `boss_appeared` | `boss` が added にある |
| `combat_state` | `enemy_appeared` | `enemy` が added にある |

phase の優先順位は `boss_appeared`、`enemy_appeared`、`combat_start`、`combat_end` とする。ボス出現や敵出現は発話価値が高いため、戦闘開始より具体的な phase を優先する。

## Salience

salience は次の要素から計算する。

- label の追加/消失
- UI element の追加/消失
- summary change
- confidence delta
- semantic event bonus

semantic event は発話価値が高いので、汎用 label change より salience を上げる。ただし最終的に喋るかは `should_speak` と `CommentPolicy` の suppression で決まる。

## Metadata

scene event metadata には次を入れる。

- `source="scene"`
- `added`
- `removed`
- `ui_added`
- `ui_removed`
- `summary_changed`
- `confidence_delta`
- `semantic_event`
- `event_phase`

`semantic_event` は semantic rule に当たった時だけ event kind と同じ値になる。汎用差分の場合は `None`。

`event_phase` は該当する semantic event に小分類がある場合だけ入れる。現時点では `combat_state` のみが対象。

## Out Of Scope

EventDetector は、まだ複雑な画像理解や長期文脈の推論をしない。以下は別レイヤーまたは将来の adapter で扱う。

- 画像ピクセルからの高精度な物体検出
- HP ゲージ量の数値比較
- OCR による全文理解
- LLM による自由分類
- 長期的な攻略状況の推定

まずは Vision adapter や fixture が出す label contract を安定させ、その label から「反応すべきイベント」を確実に増やす。
