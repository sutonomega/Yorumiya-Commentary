from __future__ import annotations

import argparse

from yorumiya_commentary import export_commentary_overlay_video


def main() -> None:
    parser = argparse.ArgumentParser(description="review.jsonl のcomment字幕と読み上げ音声をMP4へ重ねる")
    parser.add_argument("video", help="元MP4")
    parser.add_argument("review_jsonl", help="comment / audio_path を含む review.jsonl")
    parser.add_argument("output", help="出力MP4")
    parser.add_argument("--work-dir", default=None, help="字幕ASSなどの中間ファイル出力先")
    parser.add_argument("--subtitle-duration", type=float, default=3.0, help="字幕を表示する秒数")
    parser.add_argument("--no-original-audio", action="store_true", help="元動画音声をmixしない")
    args = parser.parse_args()

    result = export_commentary_overlay_video(
        args.video,
        args.review_jsonl,
        args.output,
        work_dir=args.work_dir,
        subtitle_duration_seconds=args.subtitle_duration,
        include_original_audio=not args.no_original_audio,
    )
    print(f"output: {result.output_path}")
    print(f"subtitle: {result.subtitle_path}")
    print(f"comments: {result.comment_count}")
    print(f"audio files: {result.audio_count}")


if __name__ == "__main__":
    main()
