# Review Overlay Export

UI 実装前の暫定確認として、`review.jsonl` から comment 字幕と読み上げ音声入りのMP4を生成できる。

入力は次の3つである。

- 元MP4
- `review.jsonl`
- 出力MP4 path

`review.jsonl` は、`timestamp`、`comment`、`audio_path` を含む行を使う。
`comment` は字幕としてburn-inし、`audio_path` のwavは `timestamp` に合わせてmixする。
元動画に音声がある場合は、既定で元音声を少し下げて読み上げ音声とmixする。

日本語字幕をburn-inするには、ffmpeg / libass から参照できるCJKフォントが必要である。
Ubuntu / WSL では `fonts-noto-cjk` などを入れておく。

```bash
sudo apt-get install -y fonts-noto-cjk
```

## Command

```bash
source .venv/bin/activate
PYTHONPATH=src python scripts/export_review_overlay.py \
  tests/fixtures/manual/Legacy.mp4 \
  tests/fixtures/manual/legacy_voice_review_full_2s/review.jsonl \
  tests/fixtures/manual/legacy_voice_review_full_2s/commentary_overlay.mp4
```

元動画音声を入れず、読み上げ音声だけにする場合:

```bash
source .venv/bin/activate
PYTHONPATH=src python scripts/export_review_overlay.py \
  tests/fixtures/manual/Legacy.mp4 \
  tests/fixtures/manual/legacy_voice_review_full_2s/review.jsonl \
  tests/fixtures/manual/legacy_voice_review_full_2s/commentary_overlay.mp4 \
  --no-original-audio
```

## API

```python
from yorumiya_commentary import export_commentary_overlay_video

result = export_commentary_overlay_video(
    "tests/fixtures/manual/Legacy.mp4",
    "tests/fixtures/manual/legacy_voice_review_full_2s/review.jsonl",
    "tests/fixtures/manual/legacy_voice_review_full_2s/commentary_overlay.mp4",
)

print(result.output_path)
print(result.comment_count)
print(result.audio_count)
```

## Scope

この機能はUI前の確認用であり、字幕デザインや音量調整の最終形ではない。
目的は、実MP4を見ながら comment の出るタイミング、字幕内容、読み上げ音声をまとめて確認できるようにすることである。
