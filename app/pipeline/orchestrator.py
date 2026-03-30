from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.config import ProcessingConfig
from app.domain.events import PipelineEvent
from app.domain.models import ApprovedTarget, Detection, GuidanceResult, TrackingResult, VideoMetadata
from app.pipeline.detector import PlaceholderDetector
from app.pipeline.guidance import calculate_guidance
from app.pipeline.renderer import build_overlay_lines
from app.pipeline.tracker import PlaceholderTracker
from app.pipeline.video_io import iter_sampled_frame_indices


@dataclass(slots=True)
class FramePreview:
    frame_index: int
    detections: list[Detection] = field(default_factory=list)
    approved_target: ApprovedTarget | None = None
    tracking: TrackingResult | None = None
    guidance: GuidanceResult | None = None
    overlay_lines: list[str] = field(default_factory=list)
    events: list[PipelineEvent] = field(default_factory=list)


class PlaceholderPipelineOrchestrator:
    """Deterministic Milestone 1 preview path."""

    def __init__(
        self,
        detector: PlaceholderDetector | None = None,
        tracker: PlaceholderTracker | None = None,
    ) -> None:
        self.detector = detector or PlaceholderDetector()
        self.tracker = tracker or PlaceholderTracker()

    def build_preview(
        self,
        metadata: VideoMetadata,
        config: ProcessingConfig,
        max_processed_frames: int = 6,
    ) -> list[FramePreview]:
        config.validate()

        previews: list[FramePreview] = []
        approved_target: ApprovedTarget | None = None

        for frame_index in iter_sampled_frame_indices(
            frame_count=metadata.frame_count,
            frame_sampling_interval=config.frame_sampling_interval,
        ):
            if len(previews) >= max_processed_frames:
                break

            events = [
                PipelineEvent(
                    stage="frame_iteration",
                    message="Frame selected by sampling interval.",
                    frame_index=frame_index,
                )
            ]
            detections = self.detector.detect(frame_index)

            if detections:
                events.append(
                    PipelineEvent(
                        stage="detection",
                        message="Placeholder detection generated.",
                        frame_index=frame_index,
                    )
                )

            if detections and approved_target is None:
                best_detection = max(detections, key=lambda detection: detection.confidence)
                approved_target = ApprovedTarget(
                    target_id="placeholder-target-1",
                    approval_frame=frame_index,
                    initial_bbox=best_detection.bbox,
                    initial_confidence=best_detection.confidence,
                )
                events.append(
                    PipelineEvent(
                        stage="approval",
                        message="Auto-approved highest-confidence placeholder detection for preview purposes.",
                        frame_index=frame_index,
                    )
                )

            tracking: TrackingResult | None = None
            guidance: GuidanceResult | None = None

            if approved_target is not None:
                tracking = self.tracker.track(approved_target, frame_index)
                events.append(
                    PipelineEvent(
                        stage="tracking",
                        message="Placeholder tracker updated target state.",
                        frame_index=frame_index,
                    )
                )

                if tracking.bbox is not None:
                    guidance = calculate_guidance(
                        frame_index=frame_index,
                        metadata=metadata,
                        bbox=tracking.bbox,
                        horizontal_fov_deg=config.horizontal_fov_deg,
                        vertical_fov_deg=config.vertical_fov_deg,
                    )
                    events.append(
                        PipelineEvent(
                            stage="guidance",
                            message="Guidance offsets calculated from frame center and tracked target.",
                            frame_index=frame_index,
                        )
                    )

            previews.append(
                FramePreview(
                    frame_index=frame_index,
                    detections=detections,
                    approved_target=approved_target,
                    tracking=tracking,
                    guidance=guidance,
                    overlay_lines=build_overlay_lines(tracking=tracking, guidance=guidance),
                    events=events,
                )
            )

        return previews
