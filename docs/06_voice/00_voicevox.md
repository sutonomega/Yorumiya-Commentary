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

`VoiceSynthesisError.adapter` は失敗した adapter 名を持つ。MVP では `voicevox` を使う。

## Optional Integration

実 VOICEVOX 接続は optional integration として扱う。

- unit test は `FakeVoiceSynthesizer` と `FakeAudioPlayer` で完結させる。
- 実接続の確認は `VoicevoxClient.version()`、`audio_query()`、`synthesis()` を使う integration test / application layer で扱う。
- VOICEVOX 未起動は runtime failure ではなく、voice adapter failure として扱う。

## Offline Test Adapter

`FakeVoiceSynthesizer` は VOICEVOX 未起動でも end-to-end flow を検証するための deterministic adapter である。

MVP では、実音声品質より先に `Comment -> SpeechItem -> SpeechAudio` の contract を安定させる。

## MVP Acceptance

MVP では、実 VOICEVOX ENGINE を unit test の必須条件にしない。
代わりに次の境界が外部 service なしで確認できることを受け入れ条件にする。

- frame step で `Comment` が生成される。
- `Comment` が `SpeechItem` として queue に入る。
- speech step で `SpeechItem` が voice adapter に渡る。
- `FakeVoiceSynthesizer` が `SpeechAudio(format="fake-wav")` を返す。
- `SpeechTrace` に `synthesized`、`has_speech_item`、`has_speech_audio`、`audio_format` が残る。
- voice adapter が失敗した場合は `SpeechStepResult.skipped_reason="voice_synthesis_failed"` と `SpeechTrace.error` に残り、pipeline 全体は止まらない。

実 VOICEVOX ENGINE は local runtime の手動確認で扱う。MVP の自動テストでは adapter contract を固定し、実 engine の起動状態に依存しない。

## Playback Boundary

`AudioPlayer` は `SpeechAudio` を再生する adapter boundary である。

`RealtimePipeline.run_playback_step()` は audio player がない場合は `no_audio_player`、再生する audio がない場合は `no_audio` を返す。これにより、音声合成と再生を runtime から分けて検証できる。

`PlaybackResult.as_dict()` は playback の結果を trace / debug UI へ渡すための軽量表現である。

`FakeAudioPlayer` はテスト用 adapter であり、再生された `SpeechAudio` を記録する。`last_audio` で最後に再生された audio を確認できる。
