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

HTTP 接続や外部プロセス由来の失敗は `VoiceSynthesisError` として正規化する。runtime は失敗を `SpeechStepResult.skipped_reason = "voice_synthesis_failed"` として返し、pipeline 全体を止めない。

## Offline Test Adapter

`FakeVoiceSynthesizer` は VOICEVOX 未起動でも end-to-end flow を検証するための deterministic adapter である。

MVP では、実音声品質より先に `Comment -> SpeechItem -> SpeechAudio` の contract を安定させる。

## Playback Boundary

`AudioPlayer` は `SpeechAudio` を再生する adapter boundary である。

`RealtimePipeline.run_playback_step()` は audio player がない場合は `no_audio_player`、再生する audio がない場合は `no_audio` を返す。これにより、音声合成と再生を runtime から分けて検証できる。

`FakeAudioPlayer` はテスト用 adapter であり、再生された `SpeechAudio` を記録する。
