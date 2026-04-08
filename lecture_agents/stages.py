"""Structured agent steps: style profile, slide images, descriptions, premise, arc, narration."""

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import fitz  # PyMuPDF

from lecture_agents.utils import read_text, write_json


def run_style_profile_agent(ai: Any, transcript_path: Path) -> Dict[str, Any]:
    transcript = read_text(transcript_path)
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
    return ai.generate_json(prompt)


def rasterize_pdf_to_slides(pdf_path: Path, out_dir: Path) -> List[Path]:
    doc = fitz.open(pdf_path)
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


def run_slide_description_agent(
    ai: Any, project_dir: Path, slide_images: List[Path]
) -> List[Dict[str, Any]]:
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
        current = ai.generate_json(prompt, image_path=image)
        current["slide_number"] = idx
        all_descriptions.append(current)
    write_json(project_dir / "slide_description.json", all_descriptions)
    return all_descriptions


def run_premise_agent(ai: Any, project_dir: Path, descriptions: List[Dict[str, Any]]) -> Dict[str, Any]:
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
    premise = ai.generate_json(prompt)
    write_json(project_dir / "premise.json", premise)
    return premise


def run_arc_agent(
    ai: Any, project_dir: Path, descriptions: List[Dict[str, Any]], premise: Dict[str, Any]
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
    arc = ai.generate_json(prompt)
    write_json(project_dir / "arc.json", arc)
    return arc


def run_narration_agent(
    ai: Any,
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
- Match the instructor's speaking style using style.json (tone, pacing, fillers, framing).
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
        item = ai.generate_json(prompt, image_path=image)
        item["slide_number"] = idx
        item["slide_description"] = descriptions[idx - 1]
        narrations.append(item)
    write_json(project_dir / "slide_description_narration.json", narrations)
    return narrations


def synthesize_slide_audio(tts: Any, slide_images: List[Path], narrations: List[Dict[str, Any]], out_dir: Path) -> None:
    if len(slide_images) != len(narrations):
        raise RuntimeError("Mismatch between slide count and narration count.")
    for idx, _ in enumerate(slide_images, start=1):
        text = narrations[idx - 1]["narration"]
        out = out_dir / f"slide_{idx:03d}.mp3"
        tts.synthesize_to_mp3(text, out)


def assemble_video_segments(
    pdf_path: Path, slide_images: List[Path], audio_dir: Path, segment_dir: Path, project_dir: Path
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

    output_name = pdf_path.with_suffix(".mp4").name
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
