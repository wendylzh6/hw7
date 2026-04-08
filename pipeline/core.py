import base64
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import fitz  # PyMuPDF
import requests
from dotenv import load_dotenv


def _timestamp_project_name() -> str:
    return f"project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _clean_json_text(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    return stripped


def _require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required and not found on PATH.")
    if shutil.which("ffprobe") is None:
        raise RuntimeError("ffprobe is required and not found on PATH.")


@dataclass
class AIClient:
    api_key: str
    model: str = "gemini-2.5-flash"

    @classmethod
    def from_env(cls) -> "AIClient":
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("Missing GEMINI_API_KEY in environment.")
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
        if image_path:
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
        cleaned = _clean_json_text(text)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Model did not return valid JSON.\n{text}") from exc


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


class LectureVideoPipeline:
    def __init__(self, pdf_path: Path, transcript_path: Path, projects_root: Path) -> None:
        load_dotenv()
        _require_ffmpeg()
        self.pdf_path = pdf_path
        self.transcript_path = transcript_path
        self.projects_root = projects_root
        self.ai = AIClient.from_env()
        self.tts = ElevenLabsTTS.from_env()

    def run(self, instructor_name: str = "the instructor") -> Path:
        self.projects_root.mkdir(parents=True, exist_ok=True)
        project_dir = self.projects_root / _timestamp_project_name()
        slide_img_dir = project_dir / "slide_images"
        audio_dir = project_dir / "audio"
        segment_dir = project_dir / "segments"
        slide_img_dir.mkdir(parents=True, exist_ok=True)
        audio_dir.mkdir(parents=True, exist_ok=True)
        segment_dir.mkdir(parents=True, exist_ok=True)

        style_path = Path("style.json")
        if not style_path.exists():
            style = self._make_style_json()
            _write_json(style_path, style)
        style = json.loads(style_path.read_text(encoding="utf-8"))

        slide_images = self._rasterize_slides(slide_img_dir)
        descriptions = self._make_slide_descriptions(project_dir, slide_images)
        premise = self._make_premise(project_dir, descriptions)
        arc = self._make_arc(project_dir, descriptions, premise)
        narrations = self._make_narrations(
            project_dir, slide_images, style, premise, arc, descriptions, instructor_name
        )
        self._synthesize_audio(slide_images, narrations, audio_dir)
        output_video = self._assemble_video(slide_images, audio_dir, segment_dir, project_dir)
        return output_video

    def _make_style_json(self) -> Dict[str, Any]:
        transcript = _read_text(self.transcript_path)
        prompt = f"""
You are an analyst extracting speaking style from a lecture transcript.
Return JSON only (no markdown).
Create structured fields describing:
- tone
- pacing
- sentence_complexity
- filler_words (array)
- rhetorical_patterns
- framing_patterns
- transitions
- audience_engagement_signals
- humor_or_personality_markers
- do_and_dont_for_narration

Transcript:
{transcript}
"""
        return self.ai.generate_json(prompt)

    def _rasterize_slides(self, out_dir: Path) -> List[Path]:
        doc = fitz.open(self.pdf_path)
        slide_paths: List[Path] = []
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        for idx, page in enumerate(doc, start=1):
            pix = page.get_pixmap(matrix=mat, alpha=False)
            out = out_dir / f"slide_{idx:03d}.png"
            pix.save(out)
            slide_paths.append(out)
        doc.close()
        return slide_paths

    def _make_slide_descriptions(self, project_dir: Path, slide_images: List[Path]) -> List[Dict[str, Any]]:
        all_descriptions: List[Dict[str, Any]] = []
        for idx, image in enumerate(slide_images, start=1):
            previous = json.dumps(all_descriptions, indent=2)
            prompt = f"""
You are describing lecture slides for downstream narration.
Return JSON only with fields:
- slide_number
- title_guess
- key_points (array)
- visuals (array)
- equations_or_code (array)
- technical_terms (array)
- pedagogical_role
- continuity_with_previous_slides

Current slide number: {idx}
Previous slide descriptions:
{previous}
"""
            current = self.ai.generate_json(prompt, image_path=image)
            current["slide_number"] = idx
            all_descriptions.append(current)
        _write_json(project_dir / "slide_description.json", all_descriptions)
        return all_descriptions

    def _make_premise(self, project_dir: Path, descriptions: List[Dict[str, Any]]) -> Dict[str, Any]:
        prompt = f"""
Given slide descriptions for a lecture, build a structured premise.
Return JSON only with fields:
- thesis
- scope
- audience
- learning_objectives (array)
- prerequisites (array)
- expected_takeaways (array)
- constraints_or_non_goals (array)

slide_description.json:
{json.dumps(descriptions, indent=2)}
"""
        premise = self.ai.generate_json(prompt)
        _write_json(project_dir / "premise.json", premise)
        return premise

    def _make_arc(
        self, project_dir: Path, descriptions: List[Dict[str, Any]], premise: Dict[str, Any]
    ) -> Dict[str, Any]:
        prompt = f"""
Create a structured lecture arc consistent with the premise and slides.
Return JSON only with fields:
- acts (array of objects with name, slide_range, purpose)
- knowledge_progression (array)
- tension_and_release_pattern
- recap_points (array)
- final_call_to_action

premise.json:
{json.dumps(premise, indent=2)}

slide_description.json:
{json.dumps(descriptions, indent=2)}
"""
        arc = self.ai.generate_json(prompt)
        _write_json(project_dir / "arc.json", arc)
        return arc

    def _make_narrations(
        self,
        project_dir: Path,
        slide_images: List[Path],
        style: Dict[str, Any],
        premise: Dict[str, Any],
        arc: Dict[str, Any],
        descriptions: List[Dict[str, Any]],
        instructor_name: str,
    ) -> List[Dict[str, Any]]:
        narrations: List[Dict[str, Any]] = []
        for idx, image in enumerate(slide_images, start=1):
            previous_narrations = json.dumps(narrations, indent=2)
            prompt = f"""
Generate narration for one lecture slide.
Return JSON only with fields:
- slide_number
- narration
- speaking_notes (array)

Requirements:
- Use style.json voice features.
- Stay consistent with premise.json and arc.json.
- Use slide description for factual grounding.
- Use prior narration for continuity.
- Keep narration concise but complete.
- If this is slide 1 (title slide), speaker must introduce themselves as "{instructor_name}"
  and give a short summary of the lecture topic.

style.json:
{json.dumps(style, indent=2)}

premise.json:
{json.dumps(premise, indent=2)}

arc.json:
{json.dumps(arc, indent=2)}

current_slide_description:
{json.dumps(descriptions[idx - 1], indent=2)}

all_previous_slide_descriptions:
{json.dumps(descriptions[: idx - 1], indent=2)}

all_prior_narrations:
{previous_narrations}
"""
            item = self.ai.generate_json(prompt, image_path=image)
            item["slide_number"] = idx
            item["slide_description"] = descriptions[idx - 1]
            narrations.append(item)
        _write_json(project_dir / "slide_description_narration.json", narrations)
        return narrations

    def _synthesize_audio(
        self, slide_images: List[Path], narrations: List[Dict[str, Any]], out_dir: Path
    ) -> None:
        if len(slide_images) != len(narrations):
            raise RuntimeError("Mismatch between slide count and narration count.")
        for idx, _ in enumerate(slide_images, start=1):
            text = narrations[idx - 1]["narration"]
            out = out_dir / f"slide_{idx:03d}.mp3"
            self.tts.synthesize_to_mp3(text, out)

    def _assemble_video(
        self, slide_images: List[Path], audio_dir: Path, segment_dir: Path, project_dir: Path
    ) -> Path:
        segment_paths: List[Path] = []
        for idx, image in enumerate(slide_images, start=1):
            audio = audio_dir / f"slide_{idx:03d}.mp3"
            segment = segment_dir / f"segment_{idx:03d}.mp4"
            cmd = [
                "ffmpeg",
                "-y",
                "-loop",
                "1",
                "-i",
                str(image),
                "-i",
                str(audio),
                "-c:v",
                "libx264",
                "-tune",
                "stillimage",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                str(segment),
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            segment_paths.append(segment)

        manifest = project_dir / "segments.concat.txt"
        lines = [f"file '{p.resolve()}'" for p in segment_paths]
        manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")

        output_name = self.pdf_path.with_suffix(".mp4").name
        output_video = project_dir / output_name
        concat_cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(manifest),
            "-c",
            "copy",
            str(output_video),
        ]
        subprocess.run(concat_cmd, check=True, capture_output=True)
        return output_video

