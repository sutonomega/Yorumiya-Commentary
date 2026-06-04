# Prompt Design

Prompt は system、context、memory、event、output rule に分ける。

- system: Yorumiya の振る舞いと禁止事項。
- context: scene、audio、vad、emotion、mode。
- memory: 関連する短期、長期 memory。
- event: 何が変化したか、発話すべきか。
- output rule: 1文、短く、説明しすぎない。

## Comment Policy

MVP の `CommentGenerator` は prompt 実行そのものより、発話判断の policy を先に安定させる。

- `min_salience`: event が発話対象になる最低 salience。
- `vad_interrupt_salience`: 人が話していても割り込める重要度。
- `stale_after_seconds`: 古くなった context を喋らないための期限。
- `max_length`: 1回の comment の最大長。

## Event Phase Comment

`event_phase` がある event は、汎用 event kind より先に phase 専用の短い comment を選ぶ。
phase comment は最優先で、event kind、emotion、description より先に返す。

MVP では `combat_state` の phase を対象にする。

| event_phase | comment 方針 |
| --- | --- |
| `combat_start` | 戦闘が始まったことを短く拾う |
| `enemy_appeared` | 敵が出てきたことを拾う |
| `boss_appeared` | ボス登場として強めに拾う |
| `combat_end` | 戦闘が落ち着いたことを拾う |

phase comment は説明しすぎず、1文で自然に反応する。該当 phase がない場合は従来の event kind / emotion / description ベースの comment に戻す。

## Event Kind Comment

phase を持たない semantic event は、event kind ごとに短い comment を選ぶ。

MVP では `critical_moment` を対象にする。`critical_moment` はダメージ、危機、決着など複数の意味を含むため、細かく断定せず「今のは大きいね」と汎用的に反応する。

## Suppression Reason

Quiet AI では、生成した comment だけでなく「なぜ黙ったか」を追える必要がある。

- `vad_speech`: 人声検出中のため抑制。
- `low_salience`: event の重要度が低いため抑制。
- `repeated_comment`: 直近 memory と同じ発話になるため抑制。
- `stale_context`: context が古いため抑制。
- `no_signal`: 発話材料がないため抑制。

この reason は prompt tuning より前の runtime 調整に使う。
