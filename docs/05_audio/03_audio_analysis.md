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

## Transcript Adapter

`WhisperTranscriber` は external adapter の返り値を `Transcript` に正規化する。

adapter が返せるもの:

- `Transcript`: そのまま受け取り、text trim、confidence clamp、time range 補正を行う。
- `dict`: `text`、`timestamp`、`start`、`end`、`confidence` を読み取る。
- `str`: text として扱い、`TranscriptPolicy.string_confidence` を使う。
- `None`: 空 transcript として扱う。

`TranscriptPolicy` は fallback confidence を管理する。実 Whisper adapter は raw payload を core に漏らさず、この境界で `Transcript` に変換する。

## Runtime Trace

`AudioContextTrace` は runtime の `PipelineTrace` に含まれる audio 観測データである。

- `AudioAnalyzer` の `loudness`、`atmosphere`、`event`、`rms`、`peak` を記録する。
- `VoiceActivityDetector` の `is_speech`、`speech_ratio`、`reason`、`active_samples` を記録する。
- `WhisperTranscriber` の transcript は raw text を保存せず、存在有無と confidence だけを記録する。

これにより、Quiet AI が「人が話しているから黙った」のか、「音声はあるが発話ではない」のかを trace から確認できる。

## Audio Event Detection

`AudioEventDetector` は `AudioFeatures` から音声由来の `CommentaryEvent` を作る。

- `audio_impact`: `AudioFeatures.event == "impact"` の時に作る。
- `audio_excited`: `atmosphere == "excited"` の時に作る。
- `audio_active`: `atmosphere == "active"` の時に作る。

`RealtimePipeline` は scene event と audio event の salience を比較し、高い方を `CommentaryContext.event` に採用する。これにより、画面変化が小さくても大きな効果音や盛り上がりを commentary の判断材料にできる。
