"""JSON, paths, ffmpeg checks, project naming."""

import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


def timestamp_project_name() -> str:
    return f"project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def clean_json_text(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    return stripped


def require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required and not found on PATH.")
    if shutil.which("ffprobe") is None:
        raise RuntimeError("ffprobe is required and not found on PATH.")
