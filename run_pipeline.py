import argparse
from pathlib import Path

from pipeline.core import LectureVideoPipeline


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
    output_video = pipeline.run(instructor_name=args.instructor_name)
    print(f"Pipeline complete. Video written to: {output_video}")


if __name__ == "__main__":
    main()

