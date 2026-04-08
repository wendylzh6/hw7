# Lecture PDF Narration Pipeline

This repository creates a narrated lecture video from:

- a lecture slide PDF
- a lecture transcript text file

It implements:

1. `style.json` generation at repo root (from transcript)
2. project creation under `projects/project_<YYYYMMDD_HHMMSS>/`
3. slide rasterization to `slide_images/slide_###.png`
4. per-slide AI descriptions into `slide_description.json`
5. premise generation into `premise.json`
6. arc generation into `arc.json`
7. per-slide narrations into `slide_description_narration.json`
8. per-slide TTS MP3 files under `audio/slide_###.mp3`
9. ffmpeg segment mux + concat into `<pdf_basename>.mp4`

## Setup

Prerequisites:

- Python 3.10+
- `ffmpeg` and `ffprobe` on `PATH`
- Gemini API key
- ElevenLabs API key + voice ID

Install:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env` in repo root:

```bash
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=...
ELEVENLABS_MODEL_ID=eleven_multilingual_v2
```

## Run

```bash
python run_pipeline.py \
  --pdf "/path/to/Lecture_17_AI_screenplays.pdf" \
  --transcript "/path/to/lecture_17_transcript.txt" \
  --instructor-name "Dr. Smith"
```

Output project is created under `projects/project_<timestamp>/` and final video is:

- `projects/project_<timestamp>/Lecture_17_AI_screenplays.mp4`

## Notes

- Narration generation is sequential and includes prior narrations for continuity.
- On slide 1, narration is prompted to include instructor introduction and brief lecture summary.
- Segment duration follows audio using ffmpeg `-shortest` to avoid silent tails.
- This implementation is inspired by the staged architecture used in [`zlisto/video_summarizer`](https://github.com/zlisto/video_summarizer.git).

