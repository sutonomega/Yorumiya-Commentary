# Pipeline

Yorumiya Commentary は、動画と音声を小さな状態へ変換し、変化がある時だけ短く反応する。

1. video input が frame と timestamp を供給する。
2. frame sampler が解析周期を制御する。
3. scene analyzer が現在の画面状態を自然言語化する。
4. event detector が前回との差分から発話価値を判定する。
5. audio / VAD / Whisper が音量、人声、会話内容を補助情報として渡す。
6. emotion estimator が場の盛り上がりと雰囲気を推定する。
7. comment generator が短い発話候補を作る。
8. queue と scheduler が発話タイミングを制御する。
9. VOICEVOX adapter が音声化する。
