# Lecture PDF → narrated video (multi-stage agents)

Classroom-scale pipeline: **structured AI steps** (style profile, slide descriptions, premise, arc, narration) → **text-to-speech** → **ffmpeg** (one still per slide, audio-synced segments, concatenated `.mp4`). Narration is steered by **`style.json`**, derived from the **lecture transcript**, so the spoken voice matches the instructor’s style (tone, pacing, fillers, framing).

Architecture is inspired by the multi-stage agent layout in [**zlisto/awesome-o**](https://github.com/zlisto/awesome-o.git) (premise → arc → structured JSON under `projects/`) and by [**zlisto/video_summarizer**](https://github.com/zlisto/video_summarizer.git) (shot/storyboard → render).

## Agentic flow

```text
Captions_English.txt  →  style.json (repo root)
       ↓
Lecture_17_AI_screenplays.pdf  →  slide_images/slide_NNN.png
       ↓
slide_description.json  →  premise.json  →  arc.json
       ↓
slide_description_narration.json
       ↓
audio/slide_NNN.mp3  (ElevenLabs)  →  ffmpeg segments  →  single .mp4
```

## Repository layout

```text
your-repo/
├── README.md
├── Lecture_17_AI_screenplays.pdf   # deck at repo root for graders
├── Captions_English.txt            # lecture transcript (input)
├── style.json                      # generated on first run (gitignored; see style.example.json)
├── requirements.txt
├── run_lecture_pipeline.py         # entrypoint — run from repo root
├── lecture_agents/                 # agent implementation (multi-module)
│   ├── __init__.py
│   ├── repo_paths.py
│   ├── env_loader.py
│   ├── utils.py
│   ├── clients.py                  # Gemini / OpenAI / ElevenLabs
│   ├── stages.py                   # style, rasterize, premise, arc, narration, ffmpeg
│   └── pipeline.py                 # LectureVideoPipeline orchestration
├── gemini.env.example              # copy to gemini.env (tracked template)
├── style.example.json
├── slide_images/                   # empty placeholder
├── audio/                          # empty placeholder
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

Generated **PNG, MP3, MP4**, and **segments** are in `.gitignore`. JSON under `projects/` is not ignored.

## Requirements

- Python 3.10+
- **`ffmpeg`** + **`ffprobe`** on `PATH` (for the final video step)
- **AI**: `GEMINI_API_KEY` **or** `GOOGLE_API_KEY` (Gemini), **or** `OPENAI_API_KEY` — set in **`gemini.env`** (copy from `gemini.env.example`). Same key naming idea as [awesome-o’s `.env` docs](https://github.com/zlisto/awesome-o.git).
- **TTS (optional)**: `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID` — omit to stop after `slide_description_narration.json`.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp gemini.env.example gemini.env
# edit gemini.env and add your keys
```

## Run (from repo root)

```bash
python run_lecture_pipeline.py \
  --pdf Lecture_17_AI_screenplays.pdf \
  --transcript Captions_English.txt \
  --instructor-name "Dr. Smith"
```

With ElevenLabs + ffmpeg configured, the final video is under the new project folder, basename matching the PDF (e.g. `Lecture_17_AI_screenplays.mp4`).

## Notes

- Narration is **sequential**; each slide uses **prior narrations** for continuity.
- Slide **1** prompts a **title-slide intro** + short topic summary.
- If ElevenLabs is missing, see `AUDIO_VIDEO_SKIPPED.txt` in the project folder.
