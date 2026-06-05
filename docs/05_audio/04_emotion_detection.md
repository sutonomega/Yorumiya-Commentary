# Emotion Detection

感情推定は人間の内面を断定しない。event salience、音量、VAD を使い、場の盛り上がり、雰囲気、発話優先度を推定する。

## Scene Event Hints

`critical_moment` は salience だけではなく、event metadata の label も軽い emotion hint として使う。

- `explosion` / `effect`: 大きな画面エフェクトとして `surprised` を返す。
- `danger` / `damage` / `hit`: 危険や被弾として `danger` を返す。

これらは人間の感情ではなく、実況側が感じ取る場の雰囲気である。該当しない場合は従来通り excitement の値から `calm` / `interested` / `excited` を選ぶ。

`PipelineTrace` には `emotion`、`emotion_atmosphere`、`emotion_excitement` を出し、comment がどの雰囲気で判断されたかを追えるようにする。
