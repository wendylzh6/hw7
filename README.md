# Lecture PDF → narrated video

Multi-stage **AI agents** (style profile from transcript, slide descriptions, premise, arc, narration) → **text-to-speech** → **ffmpeg** (one still per slide, audio length drives segment duration, concatenated into one `.mp4`). Narration follows **`style.json`**, derived from the lecture transcript.

Implementation patterns are informed by [zlisto/awesome-o](https://github.com/zlisto/awesome-o.git) (structured JSON under `projects/`) and [zlisto/video_summarizer](https://github.com/zlisto/video_summarizer.git) (pipeline stages → render). **Repository layout below is fixed**; only behavior inside `lecture_agents/` evolves.

## Repository layout

```text
your-repo/
├── README.md
├── style.json
├── Lecture_17_AI_screenplays.pdf
├── requirements.txt
├── run_lecture_pipeline.py    # entrypoint for the agentic flow
├── lecture_agents/            # agent code
└── projects/
    └── project_YYYYMMDD_HHMMSS/
        ├── premise.json
        ├── arc.json
        ├── slide_description.json
        └── slide_description_narration.json
```

`style.json` is written at the **repository root** the first time you run the pipeline (from your transcript). You may commit it after generation.

## Runtime outputs (gitignored)

When you run the pipeline, each `projects/project_…/` folder also gains **`slide_images/`** (PNGs), **`audio/`** (MP3s), optional **ffmpeg `segments/`**, and a final **`.mp4`** named like the PDF. Those paths are listed in `.gitignore` so large binaries are not committed.

## Setup

- Python 3.10+
- **`ffmpeg`** and **`ffprobe`** on `PATH` (final video step)
- API keys in **`gemini.env`** at repo root (copy from `gemini.env.example`). Supports `GEMINI_API_KEY` or `GOOGLE_API_KEY`, or `OPENAI_API_KEY`; optional ElevenLabs for TTS.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp gemini.env.example gemini.env
# edit gemini.env
```

## Run (from repo root)

Use your lecture transcript (e.g. `Captions_English.txt` in this folder) and the PDF at the root:

```bash
python run_lecture_pipeline.py \
  --pdf Lecture_17_AI_screenplays.pdf \
  --transcript Captions_English.txt \
  --instructor-name "Dr. Smith"
```

If ElevenLabs is not configured, the run stops after narration JSON; see `AUDIO_VIDEO_SKIPPED.txt` in the new project folder.

## Notes

- Narration is sequential and uses prior slide narrations for continuity.
- Slide 1 expects a title-style intro and short topic summary.
