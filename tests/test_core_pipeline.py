import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from yorumiya_commentary import (
    AudioAnalyzer,
    AudioContextTrace,
    AudioEventDetector,
    CommentGenerator,
    CommentPolicy,
    CompanionMode,
    EventDetector,
    EventSelectionTrace,
    EmotionEstimator,
    FakeAudioPlayer,
    FakeVoiceSynthesizer,
    FileTraceRecorder,
    FrameFileInput,
    FrameSampler,
    FrameSamplingPolicy,
    MemoryStore,
    RealtimeLoop,
    RealtimePipeline,
    RealtimeScheduler,
    RuntimeTick,
    RuntimeTraceRecorder,
    RuntimeService,
    SceneAnalyzer,
    SpeechQueuePolicy,
    SpeechStyle,
    TaskQueue,
    TranscriptEventDetector,
    TranscriptPolicy,
    VideoInput,
    VoiceActivityDetector,
    VoiceActivityPolicy,
    VoiceSynthesisError,
    WhisperTranscriber,
    comment_to_speech_item,
)
from yorumiya_commentary.models import AudioChunk, Comment, CommentaryContext, CommentaryEvent, SpeechAudio, SpeechItem, Transcript, VadResult


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
        self.assertEqual(first_event.metadata["source"], "scene")
        self.assertEqual(second_event.kind, "ui_change")
        self.assertEqual(second_event.metadata["source"], "scene")
        self.assertTrue(second_event.should_speak)
        self.assertEqual(second_event.metadata["ui_added"], ["menu", "score"])

    def test_mock_video_frames_detect_scene_events_over_time(self):
        path = Path(__file__).parent / "fixtures" / "mock_videos" / "event_flow.jsonl"
        frames = list(FrameFileInput(path, fps=1).iter_frames())

        analyzer = SceneAnalyzer()
        detector = EventDetector()
        scenes = [analyzer.analyze(frame) for frame in frames]
        events = [detector.detect(scene) for scene in scenes]

        self.assertEqual(
            [scene.summary for scene in scenes],
            ["field view", "battle starts", "enemy appears", "boss appears", "critical hit lands", "back to field", "dialog choice appears"],
        )
        self.assertEqual(
            [scene.labels for scene in scenes],
            [
                ("field",),
                ("field", "battle"),
                ("field", "battle", "enemy"),
                ("battle", "enemy", "boss"),
                ("battle", "enemy", "boss", "critical", "hit"),
                ("field",),
                ("field", "dialog", "choice"),
            ],
        )
        self.assertEqual(
            [event.kind if event else None for event in events],
            ["scene_initial", "combat_state", "combat_state", "combat_state", "critical_moment", "combat_state", "dialog_event"],
        )
        self.assertEqual(
            [event.metadata.get("event_phase") if event else None for event in events],
            [None, "combat_start", "enemy_appeared", "boss_appeared", None, "combat_end", None],
        )
        self.assertTrue(all(event and event.metadata["source"] == "scene" for event in events))

    def test_event_detector_classifies_combat_state_before_generic_label_change(self):
        detector = EventDetector()
        detector.detect(SceneAnalyzer().analyze(next(VideoInput(["field view"], fps=1).iter_frames())))
        frame = next(VideoInput(["battle starts"], fps=1).iter_frames())

        event = detector.detect(SceneAnalyzer().analyze(frame))

        self.assertEqual(event.kind, "combat_state")
        self.assertEqual(event.metadata["semantic_event"], "combat_state")
        self.assertEqual(event.metadata["event_phase"], "combat_start")
        self.assertTrue(event.should_speak)

    def test_event_detector_classifies_combat_state_when_battle_labels_disappear(self):
        detector = EventDetector()
        detector.detect(SceneAnalyzer().analyze(next(VideoInput(["battle enemy"], fps=1).iter_frames())))
        frame = next(VideoInput(["field"], fps=1).iter_frames())

        event = detector.detect(SceneAnalyzer().analyze(frame))

        self.assertEqual(event.kind, "combat_state")
        self.assertEqual(event.metadata["removed"], ["battle", "enemy"])
        self.assertEqual(event.metadata["semantic_event"], "combat_state")
        self.assertEqual(event.metadata["event_phase"], "combat_end")
        self.assertTrue(event.should_speak)

    def test_event_detector_sets_enemy_appeared_phase(self):
        detector = EventDetector()
        detector.detect(SceneAnalyzer().analyze(next(VideoInput(["battle"], fps=1).iter_frames())))
        frame = next(VideoInput(["battle enemy"], fps=1).iter_frames())

        event = detector.detect(SceneAnalyzer().analyze(frame))

        self.assertEqual(event.kind, "combat_state")
        self.assertEqual(event.metadata["event_phase"], "enemy_appeared")

    def test_event_detector_sets_boss_appeared_phase(self):
        detector = EventDetector()
        detector.detect(SceneAnalyzer().analyze(next(VideoInput(["battle enemy"], fps=1).iter_frames())))
        frame = next(VideoInput(["battle enemy boss"], fps=1).iter_frames())

        event = detector.detect(SceneAnalyzer().analyze(frame))

        self.assertEqual(event.kind, "combat_state")
        self.assertEqual(event.metadata["event_phase"], "boss_appeared")

    def test_event_detector_classifies_critical_moment(self):
        detector = EventDetector()
        detector.detect(SceneAnalyzer().analyze(next(VideoInput(["battle enemy"], fps=1).iter_frames())))
        frame = next(VideoInput(["battle enemy critical hit"], fps=1).iter_frames())

        event = detector.detect(SceneAnalyzer().analyze(frame))

        self.assertEqual(event.kind, "critical_moment")
        self.assertEqual(event.metadata["semantic_event"], "critical_moment")
        self.assertTrue(event.should_speak)

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

    def test_comment_generator_uses_combat_event_phase_comments(self):
        cases = {
            "combat_start": "戦闘が始まったね",
            "enemy_appeared": "敵が出てきたね",
            "boss_appeared": "ボスだ",
            "combat_end": "ひと段落ついたね",
        }

        for phase, expected_text in cases.items():
            with self.subTest(phase=phase):
                generator = CommentGenerator()
                event = CommentaryEvent(
                    timestamp=1.0,
                    kind="combat_state",
                    description="Combat state changed",
                    salience=0.9,
                    should_speak=True,
                    metadata={"event_phase": phase},
                )

                decision = generator.evaluate(CommentaryContext(timestamp=1.0, event=event))

                self.assertFalse(decision.suppressed)
                self.assertEqual(decision.reason, "combat_state")
                self.assertEqual(decision.comment.text, expected_text)

    def test_comment_generator_falls_back_when_combat_event_phase_is_unknown(self):
        cases = (
            {"event_phase": "unknown_phase"},
            {},
        )

        for metadata in cases:
            with self.subTest(metadata=metadata):
                generator = CommentGenerator()
                event = CommentaryEvent(
                    timestamp=1.0,
                    kind="combat_state",
                    description="Combat state changed",
                    salience=0.9,
                    should_speak=True,
                    metadata=metadata,
                )

                decision = generator.evaluate(CommentaryContext(timestamp=1.0, event=event))

                self.assertFalse(decision.suppressed)
                self.assertEqual(decision.reason, "combat_state")
                self.assertEqual(decision.comment.text, "ここ、変化があったね。Combat state changed")

    def test_comment_generator_uses_critical_moment_comment(self):
        generator = CommentGenerator()
        event = CommentaryEvent(
            timestamp=1.0,
            kind="critical_moment",
            description="Critical moment detected",
            salience=0.9,
            should_speak=True,
        )

        decision = generator.evaluate(CommentaryContext(timestamp=1.0, event=event))

        self.assertFalse(decision.suppressed)
        self.assertEqual(decision.reason, "critical_moment")
        self.assertEqual(decision.comment.text, "今のは大きいね")

    def test_comment_generator_uses_objective_update_comment(self):
        generator = CommentGenerator()
        event = CommentaryEvent(
            timestamp=1.0,
            kind="objective_update",
            description="Objective changed",
            salience=0.9,
            should_speak=True,
        )

        decision = generator.evaluate(CommentaryContext(timestamp=1.0, event=event))

        self.assertFalse(decision.suppressed)
        self.assertEqual(decision.reason, "objective_update")
        self.assertEqual(decision.comment.text, "目標が更新されたね")

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

        transcript_context = CommentaryContext(
            timestamp=10.0,
            event=CommentaryEvent(timestamp=10.0, kind="label_change", description="change", salience=0.6, should_speak=True),
            transcript=Transcript(timestamp=10.0, text="user comment", start=10.0, end=11.0, confidence=0.9),
        )
        self.assertEqual(generator.evaluate(transcript_context).reason, "transcript_speech")

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

    def test_comment_generator_allows_low_confidence_transcript_and_high_salience_event(self):
        generator = CommentGenerator(
            policy=CommentPolicy(
                transcript_interrupt_confidence=0.7,
                transcript_interrupt_salience=0.8,
            )
        )
        event = CommentaryEvent(timestamp=1.0, kind="label_change", description="battle appears", salience=0.9, should_speak=True)
        high_salience_context = CommentaryContext(
            timestamp=1.0,
            event=event,
            transcript=Transcript(timestamp=1.0, text="user speaking", start=1.0, end=2.0, confidence=0.95),
        )
        low_confidence_context = CommentaryContext(
            timestamp=2.0,
            event=CommentaryEvent(timestamp=2.0, kind="label_change", description="menu appears", salience=0.7, should_speak=True),
            transcript=Transcript(timestamp=2.0, text="maybe speech", start=2.0, end=3.0, confidence=0.4),
        )

        self.assertFalse(generator.evaluate(high_salience_context).suppressed)
        low_confidence_decision = CommentGenerator(
            policy=CommentPolicy(transcript_interrupt_confidence=0.7)
        ).evaluate(low_confidence_context)
        self.assertFalse(low_confidence_decision.suppressed)

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

    def test_run_speech_step_reports_skip_reasons(self):
        pipeline_without_voice = RealtimePipeline()
        self.assertEqual(pipeline_without_voice.run_speech_step().skipped_reason, "no_voice_synthesizer")

        pipeline_with_voice = RealtimePipeline(voice_synthesizer=FakeVoiceSynthesizer())
        self.assertEqual(pipeline_with_voice.run_speech_step().skipped_reason, "no_speech")

    def test_run_speech_step_synthesizes_queued_item(self):
        fake_voice = FakeVoiceSynthesizer()
        pipeline = RealtimePipeline(voice_synthesizer=fake_voice)
        pipeline.queue.put_speech(SpeechItem(timestamp=2.0, text="hello"))

        result = pipeline.run_speech_step(now=2.0)

        self.assertTrue(result.synthesized)
        self.assertEqual(result.speech_item.text, "hello")
        self.assertEqual(result.speech_audio.text, "hello")
        self.assertEqual(pipeline.queue.state()["speech"], 0)

    def test_run_speech_step_reports_voice_failure_without_crashing(self):
        class BrokenVoice:
            def synthesize(self, item):
                raise RuntimeError("voice down")

        pipeline = RealtimePipeline(voice_synthesizer=BrokenVoice())
        pipeline.queue.put_speech(SpeechItem(timestamp=2.0, text="hello"))

        result = pipeline.run_speech_step(now=2.0)

        self.assertEqual(result.skipped_reason, "voice_synthesis_failed")
        self.assertEqual(result.speech_item.text, "hello")
        self.assertIsNone(result.speech_audio)
        self.assertIn("voice down", result.error)

    def test_runtime_playback_step_uses_audio_player_adapter(self):
        player = FakeAudioPlayer()
        pipeline = RealtimePipeline(audio_player=player)
        audio = SpeechAudio(timestamp=1.0, text="hello", audio=b"wav", format="fake-wav")

        result = pipeline.run_playback_step(audio)

        self.assertTrue(result.played)
        self.assertEqual(player.audios[0], audio)
        self.assertEqual(player.last_audio, audio)
        self.assertEqual(result.as_dict()["audio_format"], "fake-wav")
        self.assertEqual(pipeline.run_playback_step().skipped_reason, "no_audio")

    def test_voice_synthesis_error_keeps_adapter_context(self):
        error = VoiceSynthesisError("down", adapter="voicevox")

        self.assertEqual(str(error), "down")
        self.assertEqual(error.adapter, "voicevox")

    def test_process_frame_step_exposes_decision_speech_and_audio(self):
        frame = next(
            VideoInput(
                [
                    {
                        "summary": "menu opened",
                        "labels": ["menu", "score"],
                        "ui_elements": ["menu", "score"],
                        "confidence": 0.8,
                    }
                ],
                fps=1,
            ).iter_frames()
        )
        fake_voice = FakeVoiceSynthesizer()
        pipeline = RealtimePipeline(voice_synthesizer=fake_voice)

        result = pipeline.process_frame_step(frame, synthesize=True)

        self.assertFalse(result.comment_decision.suppressed)
        self.assertIsNotNone(result.speech_item)
        self.assertIsNotNone(result.speech_audio)
        self.assertEqual(result.speech_item.text, result.speech_audio.text)
        self.assertEqual(pipeline.queue.state()["speech"], 0)

    def test_process_frame_step_reports_no_signal_without_speech(self):
        video = VideoInput(["same scene", "same scene"], fps=1)
        pipeline = RealtimePipeline()
        frames = list(video.iter_frames())

        pipeline.process_frame_step(frames[0])
        result = pipeline.process_frame_step(frames[1])

        self.assertEqual(result.comment_decision.reason, "no_signal")
        self.assertIsNone(result.speech_item)

    def test_pipeline_step_result_creates_trace_for_spoken_comment(self):
        frame = next(
            VideoInput(
                [
                    {
                        "summary": "menu opened",
                        "labels": ["menu", "score"],
                        "ui_elements": ["menu", "score"],
                        "confidence": 0.8,
                    }
                ],
                fps=1,
            ).iter_frames()
        )
        pipeline = RealtimePipeline(voice_synthesizer=FakeVoiceSynthesizer())

        result = pipeline.process_frame_step(frame, synthesize=True)
        trace = result.to_trace()

        self.assertEqual(trace.timestamp, 0.0)
        self.assertEqual(trace.event_kind, "scene_initial")
        self.assertEqual(trace.event_source, "scene")
        self.assertEqual(trace.decision_reason, "scene_initial")
        self.assertEqual(trace.decision_source, "event")
        self.assertFalse(trace.suppressed)
        self.assertTrue(trace.has_comment)
        self.assertTrue(trace.has_speech_item)
        self.assertTrue(trace.has_speech_audio)
        self.assertTrue(trace.as_dict()["has_speech_audio"])

    def test_trace_step_records_suppressed_decision_and_queue_count(self):
        video = VideoInput(["same scene", "same scene"], fps=1)
        pipeline = RealtimePipeline()
        frames = list(video.iter_frames())

        pipeline.trace_step(frames[0])
        trace = pipeline.trace_step(frames[1])

        self.assertEqual(trace.decision_reason, "no_signal")
        self.assertTrue(trace.suppressed)
        self.assertFalse(trace.has_speech_item)
        self.assertEqual(trace.queue_speech_count, 0)

    def test_run_due_steps_separates_frame_and_speech_intervals(self):
        frame = next(
            VideoInput(
                [
                    {
                        "summary": "menu opened",
                        "labels": ["menu", "score"],
                        "ui_elements": ["menu", "score"],
                        "confidence": 0.8,
                    }
                ],
                fps=1,
            ).iter_frames()
        )
        scheduler = RealtimeScheduler(frame_interval=1.0, speech_interval=0.5)
        pipeline = RealtimePipeline(voice_synthesizer=FakeVoiceSynthesizer())

        first = pipeline.run_due_steps(scheduler, frame=frame, now=0.0)
        self.assertTrue(first.frame_due)
        self.assertTrue(first.speech_due)
        self.assertIsNotNone(first.frame_step)
        self.assertTrue(first.speech_step.synthesized)
        self.assertEqual(len(first.traces), 1)

        quiet = pipeline.run_due_steps(scheduler, frame=frame, now=0.25)
        self.assertFalse(quiet.frame_due)
        self.assertFalse(quiet.speech_due)
        self.assertIsNone(quiet.frame_step)
        self.assertIsNone(quiet.speech_step)

        speech_only = pipeline.run_due_steps(scheduler, frame=frame, now=0.6)
        self.assertFalse(speech_only.frame_due)
        self.assertTrue(speech_only.speech_due)
        self.assertEqual(speech_only.speech_step.skipped_reason, "no_speech")

    def test_realtime_loop_runs_deterministic_ticks(self):
        frame = next(
            VideoInput(
                [
                    {
                        "summary": "menu opened",
                        "labels": ["menu", "score"],
                        "ui_elements": ["menu", "score"],
                        "confidence": 0.8,
                    }
                ],
                fps=1,
            ).iter_frames()
        )
        loop = RealtimeLoop(
            pipeline=RealtimePipeline(voice_synthesizer=FakeVoiceSynthesizer()),
            scheduler=RealtimeScheduler(frame_interval=1.0, speech_interval=0.5),
        )

        results = loop.run(
            [
                RuntimeTick(timestamp=0.0, frame=frame),
                RuntimeTick(timestamp=0.25),
                RuntimeTick(timestamp=0.5),
            ]
        )

        self.assertTrue(results[0].frame_due)
        self.assertTrue(results[0].speech_due)
        self.assertTrue(results[0].speech_step.synthesized)
        self.assertFalse(results[1].frame_due)
        self.assertFalse(results[1].speech_due)
        self.assertFalse(results[2].frame_due)
        self.assertTrue(results[2].speech_due)
        self.assertEqual(results[2].speech_step.skipped_reason, "no_speech")

    def test_runtime_tick_result_creates_frame_and_speech_trace(self):
        frame = next(
            VideoInput(
                [
                    {
                        "summary": "menu opened",
                        "labels": ["menu", "score"],
                        "ui_elements": ["menu", "score"],
                        "confidence": 0.8,
                    }
                ],
                fps=1,
            ).iter_frames()
        )
        loop = RealtimeLoop(
            pipeline=RealtimePipeline(voice_synthesizer=FakeVoiceSynthesizer()),
            scheduler=RealtimeScheduler(frame_interval=1.0, speech_interval=0.5),
        )

        trace = loop.step(RuntimeTick(timestamp=0.0, frame=frame)).to_trace()

        self.assertTrue(trace.frame_due)
        self.assertTrue(trace.speech_due)
        self.assertEqual(trace.frame_trace.event_kind, "scene_initial")
        self.assertTrue(trace.speech_trace.synthesized)
        self.assertEqual(trace.speech_trace.audio_format, "fake-wav")
        self.assertTrue(trace.as_dict()["speech_trace"]["has_speech_audio"])

    def test_runtime_tick_trace_records_speech_skip_without_frame(self):
        loop = RealtimeLoop(
            pipeline=RealtimePipeline(voice_synthesizer=FakeVoiceSynthesizer()),
            scheduler=RealtimeScheduler(frame_interval=1.0, speech_interval=0.5),
        )
        loop.step(RuntimeTick(timestamp=0.0))

        trace = loop.step(RuntimeTick(timestamp=0.5)).to_trace()

        self.assertFalse(trace.frame_due)
        self.assertTrue(trace.speech_due)
        self.assertIsNone(trace.frame_trace)
        self.assertEqual(trace.speech_trace.skipped_reason, "no_speech")

    def test_runtime_trace_recorder_exports_jsonl(self):
        frame = next(
            VideoInput(
                [
                    {
                        "summary": "menu opened",
                        "labels": ["menu", "score"],
                        "ui_elements": ["menu", "score"],
                        "confidence": 0.8,
                    }
                ],
                fps=1,
            ).iter_frames()
        )
        loop = RealtimeLoop(
            pipeline=RealtimePipeline(voice_synthesizer=FakeVoiceSynthesizer()),
            scheduler=RealtimeScheduler(frame_interval=1.0, speech_interval=0.5),
        )
        results = loop.run([RuntimeTick(timestamp=0.0, frame=frame), RuntimeTick(timestamp=0.5)])

        recorder = RuntimeTraceRecorder()
        recorder.extend(results)
        rows = [json.loads(line) for line in recorder.to_jsonl().splitlines()]

        self.assertEqual(len(recorder.traces), 2)
        self.assertEqual(len(recorder.as_dicts()), 2)
        self.assertEqual(rows[0]["frame_trace"]["event_kind"], "scene_initial")
        self.assertTrue(rows[0]["speech_trace"]["synthesized"])
        self.assertEqual(rows[1]["speech_trace"]["skipped_reason"], "no_speech")

    def test_runtime_service_records_metrics_and_stops_gracefully(self):
        frame = next(
            VideoInput(
                [
                    {
                        "summary": "menu opened",
                        "labels": ["menu"],
                        "ui_elements": ["menu"],
                        "confidence": 0.8,
                    }
                ],
                fps=1,
            ).iter_frames()
        )
        service = RuntimeService(
            loop=RealtimeLoop(
                pipeline=RealtimePipeline(voice_synthesizer=FakeVoiceSynthesizer()),
                scheduler=RealtimeScheduler(frame_interval=1.0, speech_interval=0.5),
            )
        )

        results = service.run([RuntimeTick(timestamp=0.0, frame=frame), RuntimeTick(timestamp=0.5)])
        service.stop()
        skipped = service.step(RuntimeTick(timestamp=1.0, frame=frame))

        self.assertEqual(len(results), 2)
        self.assertIsNone(skipped)
        self.assertFalse(service.snapshot()["running"])
        self.assertEqual(service.metrics.ticks, 2)
        self.assertEqual(service.metrics.frame_steps, 1)
        self.assertEqual(service.metrics.speech_steps, 2)
        self.assertGreaterEqual(service.metrics.synthesized, 1)
        self.assertEqual(service.snapshot()["traces"], 2)

    def test_runtime_service_stop_when_done_and_file_recorder_snapshot(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "trace.jsonl"
            service = RuntimeService(file_recorder=FileTraceRecorder(path))
            results = service.run([RuntimeTick(timestamp=0.0), RuntimeTick(timestamp=0.2)], stop_when_done=True)
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(len(results), 2)
        self.assertFalse(service.is_running)
        self.assertEqual(service.snapshot()["file_recorder"], str(path))
        self.assertEqual(service.snapshot()["metrics"]["ticks"], 2)
        self.assertEqual(len(rows), 2)

    def test_runtime_service_max_ticks_keeps_forever_loop_bounded_for_tests(self):
        service = RuntimeService()

        results = service.run_forever(
            [RuntimeTick(timestamp=0.0), RuntimeTick(timestamp=0.2), RuntimeTick(timestamp=0.4)],
            max_ticks=2,
        )

        self.assertEqual(len(results), 2)
        self.assertTrue(service.is_running)
        service.stop()
        self.assertFalse(service.is_running)

    def test_file_trace_recorder_appends_jsonl(self):
        trace = RealtimeLoop().step(RuntimeTick(timestamp=0.0)).to_trace()

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "runtime" / "trace.jsonl"
            written = FileTraceRecorder(path).write([trace])
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(written, 1)
        self.assertEqual(rows[0]["timestamp"], 0.0)
        self.assertIn("frame_due", rows[0])

    def test_realtime_loop_runs_and_records_runtime_traces(self):
        frame = next(
            VideoInput(
                [
                    {
                        "summary": "menu opened",
                        "labels": ["menu"],
                        "ui_elements": ["menu"],
                        "confidence": 0.8,
                    }
                ],
                fps=1,
            ).iter_frames()
        )
        loop = RealtimeLoop(
            pipeline=RealtimePipeline(voice_synthesizer=FakeVoiceSynthesizer()),
            scheduler=RealtimeScheduler(frame_interval=1.0, speech_interval=0.5),
        )

        recorder = loop.run_recorded([RuntimeTick(timestamp=0.0, frame=frame), RuntimeTick(timestamp=0.5)])
        rows = [json.loads(line) for line in recorder.to_jsonl().splitlines()]

        self.assertEqual(len(rows), 2)
        self.assertTrue(rows[0]["frame_due"])
        self.assertEqual(rows[0]["frame_trace"]["event_source"], "scene")
        self.assertTrue(rows[0]["speech_trace"]["synthesized"])
        self.assertFalse(rows[1]["frame_due"])
        self.assertEqual(rows[1]["speech_trace"]["skipped_reason"], "no_speech")

    def test_audio_context_trace_records_audio_vad_and_transcript_state(self):
        frame = next(VideoInput(["battle critical hit"], fps=1).iter_frames())
        chunk = AudioChunk(timestamp=0.0, samples=(0.0, 0.4, 0.5, 0.2), sample_rate=4)
        transcriber = WhisperTranscriber(
            adapter=lambda audio: Transcript(
                timestamp=audio.timestamp,
                text="user speaking",
                start=audio.timestamp,
                end=audio.timestamp + 1.0,
                confidence=0.9,
            )
        )

        result = RealtimePipeline(transcriber=transcriber).process_frame_step(frame, audio=chunk)
        audio_trace = result.to_trace().audio_trace

        self.assertIsInstance(audio_trace, AudioContextTrace)
        self.assertTrue(audio_trace.has_audio)
        self.assertEqual(audio_trace.audio_loudness, "loud")
        self.assertEqual(audio_trace.audio_atmosphere, "excited")
        self.assertTrue(audio_trace.vad_is_speech)
        self.assertGreater(audio_trace.vad_speech_ratio, 0.0)
        self.assertEqual(audio_trace.vad_reason, "speech_detected")
        self.assertEqual(audio_trace.vad_active_samples, 3)
        self.assertTrue(audio_trace.has_transcript)
        self.assertEqual(audio_trace.transcript_confidence, 0.9)
        self.assertNotIn("transcript_text", audio_trace.as_dict())

    def test_voice_activity_policy_reports_detection_reasons(self):
        strict = VoiceActivityDetector(policy=VoiceActivityPolicy(threshold=0.2, min_speech_ratio=0.75, min_active_samples=3))
        low = strict.detect(AudioChunk(timestamp=1.0, samples=(0.0, 0.3, 0.0, 0.3), sample_rate=4))
        speech = strict.detect(AudioChunk(timestamp=2.0, samples=(0.3, 0.4, 0.5, 0.0), sample_rate=4))
        silent = strict.detect(AudioChunk(timestamp=3.0, samples=(), sample_rate=4))
        inactive = strict.detect(AudioChunk(timestamp=4.0, samples=(0.01, 0.02), sample_rate=4))

        self.assertFalse(low.is_speech)
        self.assertEqual(low.reason, "low_activity")
        self.assertEqual(low.active_samples, 2)
        self.assertTrue(speech.is_speech)
        self.assertEqual(speech.reason, "speech_detected")
        self.assertEqual(silent.reason, "silent")
        self.assertEqual(inactive.reason, "no_active_samples")

    def test_whisper_transcriber_normalizes_adapter_payloads(self):
        chunk = AudioChunk(timestamp=10.0, samples=(0.0, 0.1, 0.2, 0.3), sample_rate=2)

        text_transcript = WhisperTranscriber(adapter=lambda audio: " hello ").transcribe(chunk)
        dict_transcript = WhisperTranscriber(
            adapter=lambda audio: {"text": "dict text", "start": 9.0, "end": 8.0, "confidence": 1.5}
        ).transcribe(chunk)
        empty_transcript = WhisperTranscriber(adapter=lambda audio: None).transcribe(chunk)
        policy_transcript = WhisperTranscriber(
            adapter=lambda audio: "",
            policy=TranscriptPolicy(fallback_confidence=0.2, string_confidence=0.8),
        ).transcribe(chunk)

        self.assertEqual(text_transcript.text, "hello")
        self.assertEqual(text_transcript.confidence, 0.5)
        self.assertEqual(dict_transcript.text, "dict text")
        self.assertEqual(dict_transcript.start, 9.0)
        self.assertEqual(dict_transcript.end, 9.0)
        self.assertEqual(dict_transcript.confidence, 1.0)
        self.assertEqual(empty_transcript.text, "")
        self.assertEqual(empty_transcript.confidence, 0.0)
        self.assertEqual(policy_transcript.confidence, 0.2)

    def test_audio_analyzer_and_vad_produce_timestamped_results(self):
        chunk = AudioChunk(timestamp=12.0, samples=(0.0, 0.1, 0.2, 0.0, 0.4), sample_rate=5)

        vad = VoiceActivityDetector(threshold=0.05).detect(chunk)
        audio = AudioAnalyzer().analyze(chunk)

        self.assertTrue(vad.is_speech)
        self.assertEqual(vad.start, 12.0)
        self.assertEqual(vad.reason, "speech_detected")
        self.assertIn(audio.atmosphere, {"active", "excited"})

    def test_audio_event_detector_creates_commentary_event_from_impact(self):
        audio = AudioAnalyzer().analyze(AudioChunk(timestamp=2.0, samples=(0.0, 0.9, 0.1), sample_rate=3))

        event = AudioEventDetector().detect(audio)

        self.assertEqual(event.kind, "audio_impact")
        self.assertTrue(event.should_speak)
        self.assertEqual(event.metadata["source"], "audio")
        self.assertEqual(event.metadata["audio_event"], "impact")

    def test_transcript_event_detector_creates_commentary_event_without_raw_text(self):
        transcript = Transcript(timestamp=4.0, text="boss is coming", start=4.0, end=5.25, confidence=0.9)

        event = TranscriptEventDetector().detect(transcript)

        self.assertEqual(event.kind, "transcript_signal")
        self.assertEqual(event.metadata["source"], "transcript")
        self.assertEqual(event.metadata["confidence"], 0.9)
        self.assertEqual(event.metadata["text_length"], len("boss is coming"))
        self.assertNotIn("text", event.metadata)
        self.assertFalse(event.should_speak)

    def test_realtime_pipeline_uses_audio_event_when_more_salient_than_scene_event(self):
        frame = next(VideoInput(["quiet field"], fps=1).iter_frames())
        chunk = AudioChunk(timestamp=0.0, samples=(0.0, 0.9, 0.1), sample_rate=3)
        pipeline = RealtimePipeline()

        result = pipeline.process_frame_step(frame, audio=chunk)

        self.assertEqual(result.context.event.kind, "audio_impact")
        self.assertEqual(result.comment_decision.reason, "audio_impact")
        self.assertIsNotNone(result.speech_item)

    def test_pipeline_trace_records_event_selection_reason(self):
        frame = next(VideoInput(["quiet field"], fps=1).iter_frames())
        chunk = AudioChunk(timestamp=0.0, samples=(0.0, 0.9, 0.1), sample_rate=3)

        result = RealtimePipeline().process_frame_step(frame, audio=chunk)
        selection = result.to_trace().event_selection

        self.assertIsInstance(selection, EventSelectionTrace)
        self.assertEqual(selection.reason, "audio_higher_salience")
        self.assertEqual(selection.selected_source, "audio")
        self.assertEqual(selection.scene_event_kind, "scene_initial")
        self.assertEqual(selection.audio_event_kind, "audio_impact")
        self.assertGreater(selection.audio_event_salience, selection.scene_event_salience)
        self.assertEqual(selection.as_dict()["selected_kind"], "audio_impact")

    def test_pipeline_trace_records_event_source(self):
        frame = next(VideoInput(["quiet field"], fps=1).iter_frames())
        scene_trace = RealtimePipeline().process_frame_step(frame).to_trace()
        audio_trace = RealtimePipeline().process_frame_step(
            frame,
            audio=AudioChunk(timestamp=0.0, samples=(0.0, 0.9, 0.1), sample_rate=3),
        ).to_trace()

        self.assertEqual(scene_trace.event_source, "scene")
        self.assertEqual(scene_trace.as_dict()["event_source"], "scene")
        self.assertEqual(audio_trace.event_source, "audio")
        self.assertEqual(audio_trace.as_dict()["event_source"], "audio")

    def test_realtime_pipeline_records_transcript_event_selection(self):
        frame = next(
            VideoInput(
                [
                    {
                        "summary": "quiet field",
                        "labels": ["field"],
                        "confidence": 0.1,
                    }
                ],
                fps=1,
            ).iter_frames()
        )
        chunk = AudioChunk(timestamp=0.0, samples=(0.0, 0.01, 0.0), sample_rate=3)
        transcriber = WhisperTranscriber(
            adapter=lambda audio: Transcript(
                timestamp=audio.timestamp,
                text="player speaking",
                start=audio.timestamp,
                end=audio.timestamp + 1.0,
                confidence=0.95,
            )
        )

        trace = RealtimePipeline(transcriber=transcriber).process_frame_step(frame, audio=chunk).to_trace()

        self.assertEqual(trace.event_kind, "transcript_signal")
        self.assertEqual(trace.event_source, "transcript")
        self.assertEqual(trace.decision_reason, "transcript_speech")
        self.assertEqual(trace.decision_source, "transcript")
        self.assertTrue(trace.suppressed)
        self.assertEqual(trace.event_selection.selected_source, "transcript")
        self.assertEqual(trace.event_selection.reason, "transcript_higher_salience")
        self.assertEqual(trace.event_selection.transcript_event_kind, "transcript_signal")
        self.assertEqual(trace.as_dict()["event_selection"]["transcript_event_kind"], "transcript_signal")

    def test_pipeline_trace_records_vad_suppression_source(self):
        frame = next(VideoInput(["quiet field"], fps=1).iter_frames())
        chunk = AudioChunk(timestamp=0.0, samples=(0.3, 0.4, 0.3, 0.0), sample_rate=4)

        trace = RealtimePipeline().process_frame_step(frame, audio=chunk).to_trace()

        self.assertEqual(trace.decision_reason, "vad_speech")
        self.assertEqual(trace.decision_source, "vad")
        self.assertTrue(trace.suppressed)
        self.assertTrue(trace.audio_trace.vad_is_speech)
        self.assertEqual(trace.as_dict()["decision_source"], "vad")

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

    def test_companion_mode_persists_memory_and_conversation_context(self):
        companion = CompanionMode()
        companion.switch(True)
        context = CommentaryContext(
            timestamp=3.0,
            event=CommentaryEvent(timestamp=3.0, kind="audio_impact", description="Boss roar", salience=0.9, should_speak=True),
            emotion=EmotionEstimator().estimate(
                CommentaryContext(
                    timestamp=3.0,
                    event=CommentaryEvent(timestamp=3.0, kind="audio_impact", description="Boss roar", salience=0.9, should_speak=True),
                )
            ),
        )

        comment = companion.respond("この盛り上がりを覚えて", context=context)

        self.assertEqual(comment.timestamp, 3.0)
        self.assertGreater(comment.priority, 0.0)
        self.assertEqual(companion.emotion.emotion, "interested")
        self.assertEqual(companion.conversation_context()[0].user_text, "この盛り上がりを覚えて")
        self.assertIn("Boss roar", companion.memory.recall("Boss"))

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "memory.json"
            companion.memory.save_long_memory(path)
            restored = CompanionMode()
            restored.memory.load_long_memory(path)

        self.assertIn("この盛り上がりを覚えて", restored.memory.recall("盛り上がり"))

    def test_companion_mode_exposes_foundation_state_without_model_behavior(self):
        companion = CompanionMode(conversation_limit=1)
        companion.switch(True)

        first = companion.respond("最初の話")
        second = companion.respond("次の話")
        state = companion.as_dict()

        self.assertEqual(first.reason, "companion")
        self.assertEqual(second.reason, "companion")
        self.assertEqual(len(companion.conversation_context(limit=10)), 1)
        self.assertTrue(state["active"])
        self.assertEqual(state["turns"][0]["user_text"], "次の話")
        self.assertIn("次の話", state["memory"]["long_memory"])

    def test_memory_store_loads_legacy_list_and_current_dict_payloads(self):
        with TemporaryDirectory() as temp_dir:
            legacy_path = Path(temp_dir) / "legacy.json"
            current_path = Path(temp_dir) / "current.json"
            legacy_path.write_text(json.dumps(["legacy memory"], ensure_ascii=False), encoding="utf-8")
            current_path.write_text(json.dumps({"long_memory": ["current memory"]}, ensure_ascii=False), encoding="utf-8")

            memory = MemoryStore()
            memory.load_long_memory(legacy_path)
            memory.load_long_memory(current_path)

        self.assertIn("legacy memory", memory.recall("legacy"))
        self.assertIn("current memory", memory.recall("current"))


if __name__ == "__main__":
    unittest.main()
