# VOICEVOX

VOICEVOX は HTTP API adapter として接続する。`audio_query` と `synthesis` を分け、speaker、speed、volume を `SpeechItem` から反映する。

## Voice Boundary

voice module は `SpeechItem -> SpeechAudio` の adapter boundary を持つ。

```txt
Comment
  -> comment_to_speech_item
  -> SpeechItem
  -> SpeechSynthesizer
  -> SpeechAudio
```

`VoicevoxSynthesizer` は VOICEVOX HTTP API を使う実 adapter である。core pipeline は VOICEVOX が起動しているかを知らない。

## Offline Test Adapter

`FakeVoiceSynthesizer` は VOICEVOX 未起動でも end-to-end flow を検証するための deterministic adapter である。

MVP では、実音声品質より先に `Comment -> SpeechItem -> SpeechAudio` の contract を安定させる。
