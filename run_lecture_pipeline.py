import argparse
from pathlib import Path

from lecture_agents import LectureVideoPipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lecture PDF to narrated video pipeline.")
    parser.add_argument("--pdf", required=True, help="Path to lecture PDF slides.")
    parser.add_argument("--transcript", required=True, help="Path to lecture transcript text file.")
    parser.add_argument(
        "--projects-root",
        default="projects",
        help="Root directory where project_<timestamp> folders are created.",
    )
    parser.add_argument(
        "--instructor-name",
        default="the instructor",
        help="Name used in title-slide introduction.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pipeline = LectureVideoPipeline(
        pdf_path=Path(args.pdf),
        transcript_path=Path(args.transcript),
        projects_root=Path(args.projects_root),
    )
    result = pipeline.run(instructor_name=args.instructor_name)
    if result.suffix.lower() == ".mp4":
        print(f"Pipeline complete. Video written to: {result}")
    else:
        print(
            f"Pipeline complete (no video: ElevenLabs/ffmpeg not used or skipped). "
            f"Outputs in: {result}"
        )


if __name__ == "__main__":
    main()
