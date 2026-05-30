import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from yorumiya_commentary import (
    AudioAnalyzer,
    CommentGenerator,
    CommentPolicy,
    CompanionMode,
    EventDetector,
    FakeVoiceSynthesizer,
    FrameFileInput,
    FrameSampler,
    FrameSamplingPolicy,
    RealtimePipeline,
    SceneAnalyzer,
    SpeechQueuePolicy,
    SpeechStyle,
    TaskQueue,
    VideoInput,
    VoiceActivityDetector,
    comment_to_speech_item,
)
from yorumiya_commentary.models import AudioChunk, Comment, CommentaryContext, CommentaryEvent, SpeechItem, VadResult


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

    def test_scene_analyzer_normalizes_structured_payload(self):
        frame = next(
            VideoInput(
                [
                    {
                        "summary": "Battle menu score visible",
                        "labels": ["Battle", "Menu", "Menu", "HP", "x"],
                        "ui_elements": ["menu", "hp"],
                        "confidence": 1.2,
                    }
                ],
                fps=1,
            ).iter_frames()
        )

        scene = SceneAnalyzer().analyze(frame)

        self.assertEqual(scene.labels, ("battle", "menu"))
        self.assertEqual(scene.ui_elements, ("menu", "hp"))
        self.assertEqual(scene.confidence, 1.0)

    def test_frame_file_to_scene_to_event_flow_detects_ui_change(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "frames.jsonl"
            path.write_text(
                '{"timestamp": 0, "data": {"summary": "field view", "labels": ["field"], "confidence": 0.4}}\n'
                '{"timestamp": 1, "data": {"summary": "menu opened", "labels": ["field", "menu", "score"], "ui_elements": ["menu", "score"], "confidence": 0.8}}\n',
                encoding="utf-8",
            )

            frames = list(FrameFileInput(path, fps=1).iter_frames())

        analyzer = SceneAnalyzer()
        detector = EventDetector()
        first_event = detector.detect(analyzer.analyze(frames[0]))
        second_event = detector.detect(analyzer.analyze(frames[1]))

        self.assertEqual(first_event.kind, "scene_initial")
        self.assertEqual(second_event.kind, "ui_change")
        self.assertTrue(second_event.should_speak)
        self.assertEqual(second_event.metadata["ui_added"], ["menu", "score"])

    def test_frame_file_to_comment_generation_flow(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "frames.jsonl"
            path.write_text(
                '{"timestamp": 0, "data": {"summary": "field view", "labels": ["field"], "confidence": 0.4}}\n'
                '{"timestamp": 1, "data": {"summary": "menu opened", "labels": ["field", "menu", "score"], "ui_elements": ["menu", "score"], "confidence": 0.8}}\n',
                encoding="utf-8",
            )
            frames = list(FrameFileInput(path, fps=1).iter_frames())

        pipeline = RealtimePipeline()
        pipeline.process_frame(frames[0])
        context = pipeline.build_context(frames[1])
        decision = pipeline.comment_generator.evaluate(context)

        self.assertFalse(decision.suppressed)
        self.assertIsNotNone(decision.comment)
        self.assertEqual(decision.reason, "ui_change")
        self.assertIn("UI", decision.comment.text)

    def test_comment_generator_reports_suppression_reasons(self):
        generator = CommentGenerator(policy=CommentPolicy(min_salience=0.5, stale_after_seconds=1.0))
        low_event = CommentaryEvent(timestamp=10.0, kind="label_change", description="small change", salience=0.2, should_speak=False)
        low_context = CommentaryContext(timestamp=10.0, event=low_event)

        self.assertEqual(generator.evaluate(low_context).reason, "low_salience")

        speech_context = CommentaryContext(
            timestamp=10.0,
            event=CommentaryEvent(timestamp=10.0, kind="label_change", description="change", salience=0.6, should_speak=True),
            vad=VadResult(timestamp=10.0, is_speech=True, speech_ratio=0.5),
        )
        self.assertEqual(generator.evaluate(speech_context).reason, "vad_speech")

        stale_context = CommentaryContext(
            timestamp=12.5,
            event=CommentaryEvent(timestamp=10.0, kind="label_change", description="old change", salience=0.9, should_speak=True),
        )
        self.assertEqual(generator.evaluate(stale_context).reason, "stale_context")

    def test_comment_generator_suppresses_repeated_comment(self):
        generator = CommentGenerator()
        event = CommentaryEvent(
            timestamp=1.0,
            kind="label_change",
            description="battle appears",
            salience=0.8,
            should_speak=True,
            metadata={"added": ["battle"]},
        )
        context = CommentaryContext(timestamp=1.0, event=event)

        first = generator.evaluate(context)
        second = generator.evaluate(context)

        self.assertFalse(first.suppressed)
        self.assertEqual(second.reason, "repeated_comment")

    def test_comment_to_speech_item_applies_style(self):
        comment = Comment(timestamp=3.0, text="UIが動いたね", priority=0.8, reason="ui_change")
        item = comment_to_speech_item(comment, SpeechStyle(speaker=8, speed_scale=1.2, volume_scale=0.7))

        self.assertEqual(item.timestamp, 3.0)
        self.assertEqual(item.text, "UIが動いたね")
        self.assertEqual(item.speaker, 8)
        self.assertEqual(item.speed_scale, 1.2)
        self.assertEqual(item.volume_scale, 0.7)

    def test_task_queue_limits_and_drops_stale_speech(self):
        queue = TaskQueue(speech_policy=SpeechQueuePolicy(max_items=2, stale_after_seconds=5.0))
        queue.put_speech(SpeechItem(timestamp=0.0, text="first"))
        queue.put_speech(SpeechItem(timestamp=1.0, text="second"))
        queue.put_speech(SpeechItem(timestamp=2.0, text="third"))

        self.assertEqual(queue.state()["speech"], 2)
        self.assertEqual(queue.get_speech(now=6.5).text, "third")
        self.assertIsNone(queue.get_speech())

    def test_frame_file_to_fake_voice_synthesis_flow(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "frames.jsonl"
            path.write_text(
                '{"timestamp": 0, "data": {"summary": "field view", "labels": ["field"], "confidence": 0.4}}\n'
                '{"timestamp": 1, "data": {"summary": "menu opened", "labels": ["field", "menu", "score"], "ui_elements": ["menu", "score"], "confidence": 0.8}}\n',
                encoding="utf-8",
            )
            frames = list(FrameFileInput(path, fps=1).iter_frames())

        fake_voice = FakeVoiceSynthesizer()
        pipeline = RealtimePipeline(voice_synthesizer=fake_voice)
        pipeline.process_frame(frames[0])
        pipeline.process_frame(frames[1])
        audio = pipeline.synthesize_next_speech(now=1.0)

        self.assertIsNotNone(audio)
        self.assertEqual(audio.format, "fake-wav")
        self.assertTrue(audio.audio.startswith(b"FAKE-WAV:"))
        self.assertEqual(fake_voice.items[0].text, audio.text)

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
