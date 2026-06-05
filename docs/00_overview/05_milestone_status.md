# Milestone Status

This page keeps the current roadmap status separate from implementation details.

## Current Status

Phase 1 MVP is accepted for the README scope. The current system can move through video input, frame analysis, diff detection, AI comment generation boundary, and voice output boundary with tests and manual review tooling.

| Milestone | Status | Notes |
| --- | --- | --- |
| M2 MVP Commentary Pipeline | Complete for MVP | Video input -> Frame -> SceneState -> CommentaryEvent -> CommentaryContext -> Comment -> SpeechItem -> voice adapter boundary is covered by tests and review tooling. |
| M3 Realtime Foundation | Complete | Scheduler, RuntimeTick, RuntimeTickTrace, RuntimeTraceRecorder, and JSONL export are available. |
| M4 Audio Understanding | Foundation | Scene, audio, and transcript events are unified; event selection and audio-derived suppression are traceable. Quality expansion remains future work. |
| M5 Companion AI | Foundation | Memory persistence, conversation turns, emotion observation, and response skeleton exist. Rich behavior is future work. |
| M6 Voice Integration | Complete for MVP | VOICEVOX boundary, failure normalization, fake synthesizer, playback boundary, and fake player exist. Live validation is optional integration. |
| M7 Production Runtime | Foundation | RuntimeService, metrics, snapshot, graceful stop, and file trace recording exist. Always-on operations remain future work. |

## PR Split Rule

After M4, prefer one PR per responsibility:

- audio understanding and trace behavior
- companion memory / conversation behavior
- voice synthesis / playback boundary
- runtime service / metrics / recorder
- docs and test organization

This keeps review size small and makes each issue map to one visible change.
