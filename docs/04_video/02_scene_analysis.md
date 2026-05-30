# Scene Analysis

scene analyzer は frame を `SceneState` に変換する。summary、labels、UI elements、confidence を出力し、後続 module は画像そのものではなくこの状態を読む。

## Adapter Contract

`SceneAnalyzer` は次の adapter result を受け取れる。

- `SceneState`: そのまま利用する。
- `dict`: `summary` / `description` / `data`、`labels` / `objects`、`ui_elements` / `ui`、`confidence` を正規化する。
- `str`: text から labels と UI elements を軽量抽出する。

## Normalization

- labels は lowercase にし、重複を取り除く。
- `SceneAnalysisConfig.max_labels` で最大 label 数を制限する。
- `menu`、`score`、`hp`、`map`、`dialog` などは UI element として扱う。
- confidence は `0.0` から `1.0` に clamp する。

この contract により、実 Vision model を接続する前でも fixture から scene analysis の後続 flow を検証できる。
