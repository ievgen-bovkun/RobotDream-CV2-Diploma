from __future__ import annotations

from app.domain.config import ProcessingConfig
from app.pipeline.orchestrator import PlaceholderPipelineOrchestrator
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
    assert any(preview.detections for preview in previews)
    assert any(preview.approved_target is not None for preview in previews)
    assert any(preview.tracking is not None for preview in previews)
    assert any(preview.guidance is not None for preview in previews)
