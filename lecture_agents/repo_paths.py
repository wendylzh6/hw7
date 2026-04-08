"""Repository root resolution (run scripts from repo root)."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
