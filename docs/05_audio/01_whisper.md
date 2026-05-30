# Whisper

Whisper 統合は `WhisperTranscriber` の adapter として扱う。core は timestamp 付き `Transcript` を返し、faster-whisper などの実装は外側で差し込む。
