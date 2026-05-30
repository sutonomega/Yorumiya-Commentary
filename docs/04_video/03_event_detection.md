# Event Detection

event detector は前回 scene と現在 scene を比較し、追加 label、消失 label、summary 変化から salience を計算する。salience が閾値以上の時だけ発話候補にする。

## Event Kind

`EventDetector` は差分の種類に応じて event kind を分ける。

- `scene_initial`: 最初の scene。
- `ui_change`: UI element の追加・消失がある。
- `label_change`: labels の追加・消失がある。
- `scene_change`: summary のみが変わった。

## Salience

salience は次の要素から計算する。

- label の追加・消失
- UI element の追加・消失
- summary change
- confidence delta

UI change は発話価値が高いことが多いため、通常 label より重く扱う。

## Output Metadata

event metadata には `added`、`removed`、`ui_added`、`ui_removed`、`summary_changed`、`confidence_delta` を入れる。これにより、後続の comment generator が「何が変わったか」を説明できる。
