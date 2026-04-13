from __future__ import annotations

from pathlib import Path
import tempfile

import cv2
import numpy as np

from app.domain.config import ProcessingConfig
from app.domain.models import Detection, VideoMetadata
from app.pipeline.detector import BaseDetector
from app.pipeline.orchestrator import PlaceholderPipelineOrchestrator
from app.pipeline.orchestrator import RuntimeProcessingSession
from app.services.metadata_service import build_placeholder_metadata


def test_placeholder_orchestrator_generates_detection_and_tracking_preview() -> None:
    config = ProcessingConfig(frame_sampling_interval=15)
    metadata = build_placeholder_metadata()

    previews = PlaceholderPipelineOrchestrator().build_preview(
        metadata=metadata,
        config=config,
        max_processed_frames=4,
    )

    assert previews
    assert previews[0].timestamp_seconds == 0.0
    assert any(preview.detections for preview in previews)
    assert any(preview.approved_target is not None for preview in previews)
    assert any(preview.tracking is not None for preview in previews)
    assert any(preview.guidance is not None for preview in previews)


class _NoopDetector(BaseDetector):
    backend_name = "noop"

    def predict(self, frame_index: int, frame=None) -> list[Detection]:
        return []


def _write_runtime_test_video(*, frame_count: int) -> tuple[str, VideoMetadata]:
    height = 32
    width = 48
    fps = 10.0
    temp_dir = tempfile.mkdtemp(prefix="runtime-chunk-")
    video_path = Path(temp_dir) / "chunk.mp4"
    writer = cv2.VideoWriter(
        str(video_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )
    for frame_index in range(frame_count):
        frame = np.full((height, width, 3), frame_index * 20, dtype=np.uint8)
        writer.write(frame)
    writer.release()
    metadata = VideoMetadata(
        width=width,
        height=height,
        fps=fps,
        frame_count=frame_count,
        duration_seconds=frame_count / fps,
    )
    return str(video_path), metadata


def test_runtime_chunk_session_processes_frames_sequentially() -> None:
    video_path, metadata = _write_runtime_test_video(frame_count=5)
    capture = cv2.VideoCapture(video_path)
    session = RuntimeProcessingSession(
        capture=capture,
        detector=_NoopDetector(),
    )
    orchestrator = PlaceholderPipelineOrchestrator()

    try:
        first_chunk = orchestrator.build_preview_chunk_from_session(
            session=session,
            metadata=metadata,
            config=ProcessingConfig(),
            start_frame_index=0,
            max_frames=2,
        )
        second_chunk = orchestrator.build_preview_chunk_from_session(
            session=session,
            metadata=metadata,
            config=ProcessingConfig(),
            start_frame_index=first_chunk.next_frame_index,
            max_frames=2,
        )
    finally:
        capture.release()

    assert [preview.frame_index for preview in first_chunk.previews] == [0, 1]
    assert first_chunk.next_frame_index == 2
    assert [preview.frame_index for preview in second_chunk.previews] == [2, 3]
    assert second_chunk.next_frame_index == 4
