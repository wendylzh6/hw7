"""LLM (Gemini / OpenAI) and ElevenLabs TTS clients."""

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import requests

from lecture_agents.repo_paths import REPO_ROOT
from lecture_agents.utils import clean_json_text


def gemini_api_key_from_env() -> str | None:
    """Support GEMINI_API_KEY or GOOGLE_API_KEY (same pattern as zlisto/awesome-o)."""
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


@dataclass
class AIClient:
    api_key: str
    model: str = "gemini-2.5-flash"

    @classmethod
    def from_env(cls) -> "AIClient":
        key = gemini_api_key_from_env()
        if not key:
            env_path = REPO_ROOT / "gemini.env"
            hint = ""
            if env_path.exists() and env_path.stat().st_size == 0:
                hint = (
                    f" {env_path} exists but is empty on disk; save your editor buffer "
                    "or add GEMINI_API_KEY=... or GOOGLE_API_KEY=... to the file."
                )
            elif not env_path.exists():
                hint = f" Create {env_path} from gemini.env.example and add keys."
            raise RuntimeError(f"Missing GEMINI_API_KEY or GOOGLE_API_KEY in environment.{hint}")
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        return cls(api_key=key, model=model)

    def _call(self, parts: List[Dict[str, Any]]) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"role": "user", "parts": parts}]}
        response = requests.post(
            f"{url}?key={self.api_key}",
            headers=headers,
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError(f"No candidates in model response: {data}")
        return candidates[0]["content"]["parts"][0]["text"]

    def generate_json(self, prompt: str, image_path: Path | None = None) -> Dict[str, Any]:
        parts: List[Dict[str, Any]] = [{"text": prompt}]
        if image_path is not None:
            raw = image_path.read_bytes()
            parts.append(
                {
                    "inline_data": {
                        "mime_type": "image/png",
                        "data": base64.b64encode(raw).decode("utf-8"),
                    }
                }
            )
        text = self._call(parts)
        cleaned = clean_json_text(text)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Model did not return valid JSON.\n{text}") from exc


@dataclass
class OpenAIClient:
    """OpenAI Chat Completions + optional vision."""

    api_key: str
    model: str

    @classmethod
    def from_env(cls) -> "OpenAIClient":
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("Missing OPENAI_API_KEY.")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        return cls(api_key=key, model=model)

    def generate_json(self, prompt: str, image_path: Path | None = None) -> Dict[str, Any]:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)
        if image_path is not None:
            b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
            user_content: Any = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ]
        else:
            user_content = prompt

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": user_content}],
        }
        try:
            response = client.chat.completions.create(
                **kwargs, response_format={"type": "json_object"}
            )
        except Exception:
            response = client.chat.completions.create(**kwargs)
        text = response.choices[0].message.content or ""
        cleaned = clean_json_text(text)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Model did not return valid JSON.\n{text}") from exc


def make_ai_client() -> Any:
    if gemini_api_key_from_env():
        return AIClient.from_env()
    if os.getenv("OPENAI_API_KEY"):
        return OpenAIClient.from_env()
    raise RuntimeError(
        "No AI credentials: set GEMINI_API_KEY or GOOGLE_API_KEY (Gemini), or OPENAI_API_KEY "
        "in gemini.env (see gemini.env.example)."
    )


def elevenlabs_configured() -> bool:
    return bool(os.getenv("ELEVENLABS_API_KEY") and os.getenv("ELEVENLABS_VOICE_ID"))


@dataclass
class ElevenLabsTTS:
    api_key: str
    voice_id: str
    model_id: str = "eleven_multilingual_v2"

    @classmethod
    def from_env(cls) -> "ElevenLabsTTS":
        api_key = os.getenv("ELEVENLABS_API_KEY")
        voice_id = os.getenv("ELEVENLABS_VOICE_ID")
        model_id = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
        if not api_key or not voice_id:
            raise RuntimeError(
                "Missing ELEVENLABS_API_KEY or ELEVENLABS_VOICE_ID in environment."
            )
        return cls(api_key=api_key, voice_id=voice_id, model_id=model_id)

    def synthesize_to_mp3(self, text: str, out_path: Path) -> None:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
        payload = {
            "text": text,
            "model_id": self.model_id,
            "output_format": "mp3_44100_128",
        }
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        response = requests.post(url, json=payload, headers=headers, timeout=180)
        response.raise_for_status()
        out_path.write_bytes(response.content)
