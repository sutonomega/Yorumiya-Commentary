# Audio Analysis

audio analyzer は rms、peak、loudness、atmosphere、event を出力する。環境音やゲーム音の詳細分類は後続の classifier adapter で拡張する。

## Runtime Trace

`AudioContextTrace` は runtime の `PipelineTrace` に含まれる audio 観測データである。

- `AudioAnalyzer` の `loudness`、`atmosphere`、`event`、`rms`、`peak` を記録する。
- `VoiceActivityDetector` の `is_speech` と `speech_ratio` を記録する。
- `WhisperTranscriber` の transcript は raw text を保存せず、存在有無と confidence だけを記録する。

これにより、Quiet AI が「人が話しているから黙った」のか、「音声はあるが発話ではない」のかを trace から確認できる。
