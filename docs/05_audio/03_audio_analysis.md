# Audio Analysis

audio analyzer は rms、peak、loudness、atmosphere、event を出力する。環境音やゲーム音の詳細分類は後続の classifier adapter で拡張する。

## Voice Activity Policy

`VoiceActivityPolicy` は VAD の判定条件をまとめる。

- `threshold`: active sample とみなす振幅しきい値。
- `min_speech_ratio`: speech とみなす active sample 比率。
- `min_active_samples`: speech とみなす最小 active sample 数。

`VoiceActivityDetector` は `VadResult.reason` に判定理由を残す。

- `speech_detected`: speech 条件を満たした。
- `low_activity`: active sample はあるが speech 条件に届かない。
- `no_active_samples`: active sample がない。
- `silent`: sample がない。

## Runtime Trace

`AudioContextTrace` は runtime の `PipelineTrace` に含まれる audio 観測データである。

- `AudioAnalyzer` の `loudness`、`atmosphere`、`event`、`rms`、`peak` を記録する。
- `VoiceActivityDetector` の `is_speech`、`speech_ratio`、`reason`、`active_samples` を記録する。
- `WhisperTranscriber` の transcript は raw text を保存せず、存在有無と confidence だけを記録する。

これにより、Quiet AI が「人が話しているから黙った」のか、「音声はあるが発話ではない」のかを trace から確認できる。
