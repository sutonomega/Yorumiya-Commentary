# Acceptance Criteria

MVP の acceptance criteria は、機能が「完成したように見える」ことではなく、次の contract が満たされることを基準にする。

## Documentation

- overview に project purpose、goals、concept、principles、roadmap がある。
- requirements に MVP scope、functional requirements、non-functional requirements、out of scope、acceptance criteria がある。
- architecture docs と `models.py` の data flow が一致している。

## Core Implementation

- `Frame`、`SceneState`、`CommentaryEvent`、`CommentaryContext`、`Comment`、`SpeechItem` が存在する。
- frame から speech queue までの最小 flow が動く。
- VAD による発話抑制が存在する。
- memory による重複抑制が存在する。
- voice adapter boundary が存在する。

## Tests

- 外部 service なしで core tests が通る。
- video sampling と realtime pipeline の smoke test がある。
- event suppression の test がある。
- audio analyzer / VAD の test がある。
- companion skeleton の memory test がある。

## Known Limitations

次は acceptance criteria から除外する。

- 実 Whisper model の認識品質。
- 実 VOICEVOX engine の起動確認。
- OpenCV / ffmpeg による mp4 decode。
- OBS integration。
- 長時間運用の latency tuning。

これらは adapter integration issue として後続で扱う。
