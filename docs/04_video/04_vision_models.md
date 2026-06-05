# Vision Models

初期実装は adapter 境界のみを用意する。ローカル VLM、OCR、UI detector を差し替えられるよう、core は `Frame -> SceneState` の関数を受け取る。

## OpenCV Heuristic Adapter

最初の実動画確認では、外部AI modelなしで動く `OpenCVHeuristicVisionAdapter` を使えるようにする。

この adapter は本格的なゲーム理解ではない。sampled frame の brightness、彩度、明るい高彩度領域、オレンジ系の明るい領域を見て、爆発や大きなエフェクトらしい frame に `effect` / `explosion` / `critical` labels を付ける。

目的は次の通り。

- MP4から画像を読み、vision_adapter 経由で comment が変わることを実動画で確認する。
- 明るい爆発/エフェクトを `critical_moment` へ流し、「今のは大きいね」のような短文 comment を出せるようにする。
- 将来の VLM / OCR / object detector へ置き換える前の、軽量な baseline を用意する。

`export_mp4_commentary_review()` の `review.jsonl` には、直接渡した adapter 名が `vision_adapter` として出る。これにより、default metadata だけで処理したのか、`OpenCVHeuristicVisionAdapter` を通したのかを log から確認できる。

制約:

- 画像の意味理解はしない。
- UI、キャラクター、敵、字幕の読み取りはしない。
- 派手な明滅や白い画面を critical と誤検出する可能性がある。
