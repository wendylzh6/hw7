"""Orchestrates multi-stage PDF → narrated video pipeline."""

import json
from pathlib import Path

from lecture_agents.clients import ElevenLabsTTS, elevenlabs_configured, make_ai_client
from lecture_agents.env_loader import load_gemini_env
from lecture_agents.repo_paths import REPO_ROOT
from lecture_agents.stages import (
    assemble_video_segments,
    rasterize_pdf_to_slides,
    run_arc_agent,
    run_narration_agent,
    run_premise_agent,
    run_slide_description_agent,
    run_style_profile_agent,
    synthesize_slide_audio,
)
from lecture_agents.utils import require_ffmpeg, timestamp_project_name, write_json


class LectureVideoPipeline:
    """Multi-stage agentic flow (style → slides → premise → arc → narration → TTS → ffmpeg)."""

    def __init__(self, pdf_path: Path, transcript_path: Path, projects_root: Path) -> None:
        load_gemini_env()
        self.pdf_path = pdf_path
        self.transcript_path = transcript_path
        self.projects_root = projects_root
        self.ai = make_ai_client()
        self._tts: ElevenLabsTTS | None = None

    def _get_tts(self) -> ElevenLabsTTS:
        if self._tts is None:
            self._tts = ElevenLabsTTS.from_env()
        return self._tts

    def run(self, instructor_name: str = "the instructor") -> Path:
        self.projects_root.mkdir(parents=True, exist_ok=True)
        project_dir = self.projects_root / timestamp_project_name()
        slide_img_dir = project_dir / "slide_images"
        audio_dir = project_dir / "audio"
        segment_dir = project_dir / "segments"
        slide_img_dir.mkdir(parents=True, exist_ok=True)
        audio_dir.mkdir(parents=True, exist_ok=True)
        segment_dir.mkdir(parents=True, exist_ok=True)

        style_path = REPO_ROOT / "style.json"
        if not style_path.exists():
            style = run_style_profile_agent(self.ai, self.transcript_path)
            write_json(style_path, style)
        style = json.loads(style_path.read_text(encoding="utf-8"))

        slide_images = rasterize_pdf_to_slides(self.pdf_path, slide_img_dir)
        descriptions = run_slide_description_agent(self.ai, project_dir, slide_images)
        premise = run_premise_agent(self.ai, project_dir, descriptions)
        arc = run_arc_agent(self.ai, project_dir, descriptions, premise)
        narrations = run_narration_agent(
            self.ai,
            project_dir,
            slide_images,
            style,
            premise,
            arc,
            descriptions,
            instructor_name,
        )
        if not elevenlabs_configured():
            note = project_dir / "AUDIO_VIDEO_SKIPPED.txt"
            note.write_text(
                "ElevenLabs is not configured (set ELEVENLABS_API_KEY and "
                "ELEVENLABS_VOICE_ID in gemini.env). Narration JSON is complete; "
                "add keys and re-run or run a separate audio step.\n",
                encoding="utf-8",
            )
            return project_dir
        synthesize_slide_audio(self._get_tts(), slide_images, narrations, audio_dir)
        require_ffmpeg()
        return assemble_video_segments(
            self.pdf_path, slide_images, audio_dir, segment_dir, project_dir
        )
