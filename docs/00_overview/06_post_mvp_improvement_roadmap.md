# Post MVP Improvement Roadmap

MVP では、動画入力、フレーム解析、差分検出、AIコメント生成境界、音声読み上げ境界が成立した。
次の目的は、実MP4を流した時の実況密度と自然さを上げることである。

## Current Finding

`Legacy.mp4` を2秒間隔で全体処理した結果、約228秒 / 114 sampled frames に対して comment は3件だった。

主な理由:

- `OpenCVHeuristicVisionAdapter` が明るさ、画面サイズ、エフェクトらしさ程度しか見ていない。
- 同じ labels が続くと `EventDetector` は `no_signal` にしやすい。
- ただし、同じ labels でも別カット、別爆発、別演出など別要因で発生している場合がある。labels の一致だけで同じ出来事と決めない方針が必要である。
- repeated suppression は必要だが、現状では「同じ場面が続いている中で少し観察する」余地が少ない。
- dialog / OCR / object detection がないため、映像内容に沿った event が増えにくい。

この状態はMVPとしては受け入れ可能だが、実況体験としては発話が少ない。

## Phase 2-A: Speech Density Baseline

目的は、実MP4全体を流した時に、無音が長すぎない最低限の実況密度を作ること。

- brightness / color / effect ratio の変化量から `scene_change` を出す。
- labels が同じでも、frame signature、色分布、effect ratio、timestamp gap が大きく変わった場合は別イベントとして扱う。
- `no_signal` が一定時間続いた時だけ、低頻度の observation comment を許可する。
- repeated suppression は維持しつつ、時間間隔を見て再発話を許可する。
- review summary に sampled frames、comments、audio files、suppression reasons を出す。

完了目安:

- 実MP4全体レビューで comment 件数と suppression 内訳を確認できる。
- コメントが連発せず、かつ長時間0件になりにくい。

Tracking issue: [#101](https://github.com/sutonomega/Yorumiya-Commentary/issues/101)

## Phase 2-B: Vision Signal Improvement

目的は、軽量heuristicだけでは拾えない画面内容を event に変換すること。

- OCR / subtitle detection の adapter contract を追加する。
- object / scene classification の labels を受け取れるようにする。
- dialog / subtitle / menu / result / loading などのlabel contractを整理する。
- 実MP4 review で vision_adapter 名と推定metadataを追えるようにする。

完了目安:

- `dialog_event`、`objective_update`、`item_update` が実映像から増える。
- comment が単なる明暗やエフェクト反応に偏らない。

Tracking issue: [#103](https://github.com/sutonomega/Yorumiya-Commentary/issues/103)

## Phase 2-C: Comment Quality

目的は、テンプレとLLM生成の両方で、短く自然な実況を増やすこと。

- event kind / phase ごとの variant を増やす。
- Ollama prompt に「同じ言い回しを避ける」「映像から読める範囲だけ反応する」を明記する。
- comment density policy と suppression を一体で調整する。
- review.jsonl から comment 品質を人が確認しやすくする。

完了目安:

- 同じ動画を流しても同一コメントが並びにくい。
- 説明文ではなく、実況として自然な短文になる。

Tracking issue: [#102](https://github.com/sutonomega/Yorumiya-Commentary/issues/102)

## Phase 2-D: Review Output

目的は、UI前の暫定確認手段として、実MP4にcomment字幕と読み上げ音声を重ねたMP4を生成できるようにすること。

- review.jsonl の `timestamp` / `comment` / `audio_path` を使う。
- comment を字幕として映像にburn-inする。
- VOICEVOXで生成したwavをtimestampに合わせてmixする。
- 元動画音声がある場合は、読み上げ音声とmixする。
- UI実装前でも、出力MP4を見るだけで実況体験を確認できるようにする。

完了目安:

- 実MP4 review の結果から overlay付きMP4を生成できる。
- 生成物に字幕と読み上げ音声が入る。

Tracking issue: [#104](https://github.com/sutonomega/Yorumiya-Commentary/issues/104)
