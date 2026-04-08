"""Load local secrets from `gemini.env` (gitignored)."""

from dotenv import load_dotenv

from lecture_agents.repo_paths import REPO_ROOT


def load_gemini_env() -> None:
    load_dotenv(REPO_ROOT / "gemini.env")
