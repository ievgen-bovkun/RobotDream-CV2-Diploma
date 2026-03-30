from __future__ import annotations

from pathlib import Path


def build_output_targets(video_name: str, output_dir: str = "outputs") -> dict[str, Path]:
    stem = Path(video_name).stem or "session"
    base_dir = Path(output_dir)
    return {
        "annotated_video": base_dir / f"{stem}_annotated.mp4",
        "csv_log": base_dir / f"{stem}_log.csv",
        "json_log": base_dir / f"{stem}_log.json",
    }
