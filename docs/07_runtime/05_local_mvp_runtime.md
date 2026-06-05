# Local MVP Runtime

この手順は、README の MVP 項目をローカル環境で確認するための起動手順である。

MVP では、AI コメント生成はローカル LLM の Ollama、音声読み上げは VOICEVOX ENGINE を使う想定にする。

## Environment

- WSL2 Ubuntu 24.04
- Docker available
- Ollama available
- Yorumiya runs inside WSL

## Ollama

Install:

```bash
sudo apt install -y zstd
curl -fsSL https://ollama.com/install.sh | sh
```

Start service:

```bash
ollama serve
```

Model:

```bash
ollama pull qwen3:4b
```

Endpoint:

```text
http://localhost:11434
```

Health check:

```bash
curl http://localhost:11434/api/tags
```

The response should include the pulled model, for example `qwen3:4b`.

Minimal comment check:

```bash
source .venv/bin/activate
PYTHONPATH=src python - <<'PY'
from yorumiya_commentary import CommentGenerator, OllamaCommentAdapter
from yorumiya_commentary.models import CommentaryContext, CommentaryEvent, SceneState

adapter = OllamaCommentAdapter()
generator = CommentGenerator(model_adapter=adapter)
context = CommentaryContext(
    timestamp=0.0,
    scene=SceneState(0.0, "battle enemy appears", labels=("battle", "enemy"), confidence=0.9),
    event=CommentaryEvent(
        0.0,
        "combat_state",
        "enemy appeared",
        salience=0.9,
        should_speak=True,
        metadata={"event_phase": "enemy_appeared"},
    ),
)

decision = generator.evaluate(context)
print(decision.reason, decision.comment.text if decision.comment else None)
PY
```

If Ollama is unavailable or returns an empty response, Yorumiya falls back to the deterministic template comment.

## VOICEVOX ENGINE

Start VOICEVOX ENGINE with Docker:

```bash
sudo docker run --rm -it -p 50021:50021 voicevox/voicevox_engine:cpu-ubuntu20.04-latest
```

Endpoint:

```text
http://localhost:50021
```

Health check:

```bash
curl http://localhost:50021/version
```

Expected response:

```text
"latest"
```

## Yorumiya Runtime Check

Use the project virtual environment. Do not install dependencies with `pip3 install --user`.

```bash
source .venv/bin/activate
PYTHONPATH=src python -m unittest discover -s tests
```

Manual MP4 review:

```bash
source .venv/bin/activate
PYTHONPATH=src python - <<'PY'
from pathlib import Path
from yorumiya_commentary import OpenCVHeuristicVisionAdapter, export_mp4_commentary_review

video = "tests/fixtures/manual/Legacy.mp4"
out = Path("tests/fixtures/manual/legacy_review")
rows = export_mp4_commentary_review(
    video,
    out,
    vision_adapter=OpenCVHeuristicVisionAdapter(),
    sample_interval_seconds=10.0,
    max_frames=5,
)

for row in rows:
    print(row["timestamp"], row["scene_summary"], row["event_kind"], row["decision_reason"], row["comment"])
PY
```

This produces sampled frame images and `review.jsonl`.

## MVP Confirmation Scope

This document covers local service startup and health checks. It does not complete the MVP by itself.

MVP confirmation still needs issue-level checks for:

- video input
- frame analysis
- diff detection
- AI comment generation through Ollama
- voice output through VOICEVOX

If the commands above become stable and repetitive, create a separate issue for a script such as `scripts/check_local_mvp.sh`.
