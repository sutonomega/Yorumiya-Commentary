import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from yorumiya_commentary import (
    CompanionMode,
    FakeAudioPlayer,
    FakeVoiceSynthesizer,
    FileTraceRecorder,
    RealtimeLoop,
    RealtimePipeline,
    RealtimeScheduler,
    RuntimeService,
    RuntimeTick,
    VideoInput,
    WhisperTranscriber,
)
from yorumiya_commentary.models import AudioChunk, CommentaryContext, CommentaryEvent, SpeechItem, Transcript


class MilestoneSmokeTest(unittest.TestCase):
    def test_m4_audio_understanding_traces_transcript_suppression(self):
        frame = next(VideoInput([{"summary": "quiet field", "labels": ["field"], "confidence": 0.1}], fps=1).iter_frames())
        chunk = AudioChunk(timestamp=0.0, samples=(0.0, 0.01, 0.0), sample_rate=3)
        transcriber = WhisperTranscriber(
            adapter=lambda audio: Transcript(audio.timestamp, "player speaking", audio.timestamp, audio.timestamp + 1.0, 0.95)
        )

        trace = RealtimePipeline(transcriber=transcriber).process_frame_step(frame, audio=chunk).to_trace()

        self.assertEqual(trace.event_source, "transcript")
        self.assertEqual(trace.decision_source, "transcript")
        self.assertTrue(trace.suppressed)

    def test_m5_companion_foundation_tracks_memory_turns_and_emotion(self):
        companion = CompanionMode()
        context = CommentaryContext(
            timestamp=1.0,
            event=CommentaryEvent(1.0, "audio_impact", "Boss roar", 0.9, True),
        )

        comment = companion.respond("この場面を覚えて", context=context)

        self.assertEqual(comment.reason, "companion")
        self.assertEqual(companion.conversation_context()[0].user_text, "この場面を覚えて")
        self.assertIn("Boss roar", companion.memory.recall("Boss"))

    def test_m6_voice_foundation_runs_fake_synthesis_and_playback(self):
        voice = FakeVoiceSynthesizer()
        player = FakeAudioPlayer()
        pipeline = RealtimePipeline(voice_synthesizer=voice, audio_player=player)
        pipeline.queue.put_speech(SpeechItem(timestamp=1.0, text="hello"))

        speech = pipeline.run_speech_step(now=1.0)
        playback = pipeline.run_playback_step(speech.speech_audio)

        self.assertTrue(speech.synthesized)
        self.assertTrue(playback.played)
        self.assertEqual(player.last_audio.text, "hello")

    def test_m7_runtime_foundation_records_service_snapshot_and_jsonl(self):
        service = RuntimeService(
            loop=RealtimeLoop(
                pipeline=RealtimePipeline(voice_synthesizer=FakeVoiceSynthesizer()),
                scheduler=RealtimeScheduler(frame_interval=1.0, speech_interval=0.5),
            )
        )

        service.run([RuntimeTick(timestamp=0.0), RuntimeTick(timestamp=0.5)])
        service.stop()

        self.assertFalse(service.snapshot()["running"])
        self.assertEqual(service.snapshot()["metrics"]["ticks"], 2)
        self.assertEqual(len(service.recorder.to_jsonl().splitlines()), 2)

    def test_cleanup_milestone_status_doc_is_jsonl_friendly(self):
        trace = RealtimeLoop().step(RuntimeTick(timestamp=0.0)).to_trace()
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "trace.jsonl"
            FileTraceRecorder(path).write([trace])
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(rows[0]["timestamp"], 0.0)


if __name__ == "__main__":
    unittest.main()
