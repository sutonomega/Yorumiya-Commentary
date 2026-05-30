from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .models import SpeechAudio, SpeechItem


@dataclass
class VoicevoxClient:
    endpoint: str = "http://127.0.0.1:50021"
    timeout: float = 10.0

    def audio_query(self, text: str, speaker: int) -> dict:
        url = f"{self.endpoint}/audio_query?{urlencode({'text': text, 'speaker': speaker})}"
        with urlopen(Request(url, method="POST"), timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def synthesis(self, query: dict, speaker: int) -> bytes:
        url = f"{self.endpoint}/synthesis?{urlencode({'speaker': speaker})}"
        body = json.dumps(query).encode("utf-8")
        request = Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=self.timeout) as response:
            return response.read()


class VoicevoxSynthesizer:
    def __init__(self, client: VoicevoxClient | None = None):
        self.client = client or VoicevoxClient()

    def synthesize(self, item: SpeechItem) -> SpeechAudio:
        query = self.client.audio_query(item.text, item.speaker)
        query["speedScale"] = item.speed_scale
        query["volumeScale"] = item.volume_scale
        audio = self.client.synthesis(query, item.speaker)
        return SpeechAudio(timestamp=item.timestamp, text=item.text, audio=audio)
