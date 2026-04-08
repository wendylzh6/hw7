# Lecture PDF narration pipeline

Agentic flow: transcript → `style.json` → slide images → descriptions → premise → arc → narrations → optional TTS + video.

## Repository layout

```text
your-repo/
├── README.md
├── Lecture_17_AI_screenplays.pdf   # deck at repo root for graders
├── Captions_English.txt            # lecture transcript (input)
├── style.json                      # generated on first run (gitignored; see style.example.json)
├── requirements.txt
├── run_lecture_pipeline.py         # entrypoint
├── lecture_agents/                 # agent implementation
│   ├── __init__.py
│   └── core.py
├── gemini.env.example              # copy to gemini.env (tracked template; secrets stay local)
├── style.example.json
├── slide_images/                   # empty placeholder; run output also under projects/.../slide_images/
├── audio/                          # empty placeholder; run output also under projects/.../audio/
└── projects/
    └── project_YYYYMMDD_HHMMSS/
        ├── premise.json
        ├── arc.json
        ├── slide_description.json
        ├── slide_description_narration.json
        ├── slide_images/          # PNGs (gitignored)
        ├── audio/                 # MP3s (gitignored)
        ├── segments/              # ffmpeg segments (gitignored)
        └── Lecture_17_AI_screenplays.mp4   # final video (gitignored)
```

Generated **PNG, MP3, MP4**, and **segments** are listed in `.gitignore` so large binaries are not committed. JSON outputs under `projects/` are not ignored.

## Setup

- Python 3.10+
- `ffmpeg` + `ffprobe` on `PATH` (only for final video step)
- **AI**: set `GEMINI_API_KEY` (Google Gemini, preferred) **or** `OPENAI_API_KEY` in `gemini.env` (copy from `gemini.env.example`).
- **TTS (optional)**: `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID` — omit to stop after narration JSON.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp gemini.env.example gemini.env
# edit gemini.env and add your keys
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
