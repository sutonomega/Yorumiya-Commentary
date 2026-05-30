# Realtime Pipeline

realtime pipeline は module 内部の推論内容を知らず、接続順と受け渡しだけを管理する。解析周期、推論周期、発話周期は scheduler が判断し、queue が処理順序を保つ。

最小実装は `RealtimePipeline.process_frame()` に集約し、後から OBS、OpenCV、Whisper、VOICEVOX の実 adapter を差し込める構造にする。
