# Error Handling

外部 adapter の失敗は pipeline 全体を止めない。Whisper、Vision、VOICEVOX の失敗は空結果または queue 保留として扱い、ログに残す。
