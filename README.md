# Lecture PDF narration pipeline

Agentic flow: transcript → `style.json` → slide images → descriptions → premise → arc → narrations → optional TTS + video.

## Repository layout

```text
your-repo/
├── README.md
├── style.json                 # generated at repo root on first run (gitignored; see style.example.json)
├── Lecture_17_AI_screenplays.pdf
├── requirements.txt
├── run_lecture_pipeline.py    # entrypoint
├── lecture_agents/            # agent implementation
│   ├── __init__.py
│   └── core.py
├── env.example                # copy to .env and/or gemini.env
├── style.example.json         # shape reference before first run
└── projects/
    └── project_YYYYMMDD_HHMMSS/
        ├── premise.json
        ├── arc.json
        ├── slide_description.json
        ├── slide_description_narration.json
        ├── slide_images/          # PNGs per slide (created at run time)
        ├── audio/                 # if ElevenLabs configured
        └── segments/            # if video step runs
```

## Setup

- Python 3.10+
- `ffmpeg` + `ffprobe` on `PATH` (only for final video step)
- **AI**: set `GEMINI_API_KEY` (Google Gemini, preferred) **or** `OPENAI_API_KEY` in `.env` and/or `gemini.env` (see `env.example`). `gemini.env` overrides `.env` for duplicate keys.
- **TTS (optional)**: `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID` — omit to stop after narration JSON.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp env.example .env
# optional: cp env.example gemini.env  # then add keys
```

## Run

```bash
python run_lecture_pipeline.py \
  --pdf Lecture_17_AI_screenplays.pdf \
  --transcript Captions_English.txt \
  --instructor-name "Dr. Smith"
```

With ElevenLabs + ffmpeg configured, the final video is under the new project folder, named like the PDF (e.g. `Lecture_17_AI_screenplays.mp4`).

## Notes

- Narration is sequential and uses prior narrations for continuity.
- Slide 1 narration prompts a title-slide intro + short topic summary.
- Inspired by the staged layout in [`zlisto/video_summarizer`](https://github.com/zlisto/video_summarizer.git).
