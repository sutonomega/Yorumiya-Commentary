import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from yorumiya_commentary import (
    AudioAnalyzer,
    CompanionMode,
    EventDetector,
    FrameFileInput,
    FrameSampler,
    FrameSamplingPolicy,
    RealtimePipeline,
    VideoInput,
    VoiceActivityDetector,
)
from yorumiya_commentary.models import AudioChunk


class CorePipelineTest(unittest.TestCase):
    def test_video_sampling_and_realtime_pipeline_enqueues_speech(self):
        video = VideoInput(["menu score", "battle score critical hit"], fps=1)
        frames = list(FrameSampler(interval_seconds=1).sample(video.iter_frames()))

        pipeline = RealtimePipeline()
        context = pipeline.process_frame(frames[0])
        pipeline.process_frame(frames[1])

        self.assertIsNotNone(context.scene)
        self.assertGreaterEqual(pipeline.queue.state()["speech"], 1)

    def test_frame_file_input_reads_plain_and_json_lines(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "frames.jsonl"
            path.write_text('menu score\n{"timestamp": 2.5, "data": "battle critical"}\n', encoding="utf-8")

            frames = list(FrameFileInput(path, fps=1).iter_frames())

        self.assertEqual(frames[0].timestamp, 0.0)
        self.assertEqual(frames[0].data, "menu score")
        self.assertEqual(frames[1].timestamp, 2.5)
        self.assertEqual(frames[1].data, "battle critical")

    def test_frame_sampler_policy_limits_range_and_count(self):
        video = VideoInput(["f0", "f1", "f2", "f3", "f4"], fps=1)
        policy = FrameSamplingPolicy(interval_seconds=1.5, start_timestamp=1.0, end_timestamp=4.0, max_frames=2)

        frames = list(FrameSampler(policy=policy).sample(video.iter_frames()))

        self.assertEqual([frame.index for frame in frames], [1, 3])

    def test_event_detector_suppresses_unchanged_scene(self):
        video = VideoInput(["same scene", "same scene"], fps=1)
        detector = EventDetector()
        pipeline = RealtimePipeline(event_detector=detector)
        frames = list(video.iter_frames())

        first = pipeline.process_frame(frames[0])
        second = pipeline.process_frame(frames[1])

        self.assertIsNotNone(first.event)
        self.assertIsNone(second.event)

    def test_audio_analyzer_and_vad_produce_timestamped_results(self):
        chunk = AudioChunk(timestamp=12.0, samples=(0.0, 0.1, 0.2, 0.0, 0.4), sample_rate=5)

        vad = VoiceActivityDetector(threshold=0.05).detect(chunk)
        audio = AudioAnalyzer().analyze(chunk)

        self.assertTrue(vad.is_speech)
        self.assertEqual(vad.start, 12.0)
        self.assertIn(audio.atmosphere, {"active", "excited"})

    def test_realtime_pipeline_merges_audio_into_context(self):
        frame = next(VideoInput(["battle critical hit"], fps=1).iter_frames())
        chunk = AudioChunk(timestamp=0.0, samples=(0.0, 0.4, 0.5, 0.2), sample_rate=4)

        context = RealtimePipeline().process_frame(frame, audio=chunk)

        self.assertIsNotNone(context.audio)
        self.assertIsNotNone(context.vad)
        self.assertIsNotNone(context.transcript)
        self.assertIsNotNone(context.emotion)

    def test_companion_mode_remembers_user_context(self):
        companion = CompanionMode()
        companion.switch(True)

        first = companion.respond("このボス戦を覚えておいて")
        second = companion.respond("ボス戦どう見える？")

        self.assertEqual(first.reason, "companion")
        self.assertIn("ボス戦", second.text)


if __name__ == "__main__":
    unittest.main()
