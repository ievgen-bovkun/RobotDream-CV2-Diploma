from __future__ import annotations

from dataclasses import dataclass, field
import cv2

from app.domain.config import ProcessingConfig
from app.domain.events import PipelineEvent
from app.domain.models import ApprovedTarget, Detection, GuidanceCommand, GuidanceResult, TrackingResult, VideoMetadata
from app.pipeline.detector import BaseDetector, build_detector_for_config, PlaceholderDetector
from app.pipeline.guidance import calculate_guidance, calculate_guidance_command
from app.pipeline.renderer import build_overlay_lines
from app.pipeline.tracker import BaseTracker, BridgeTracker, build_tracker_for_config
from app.pipeline.video_io import iter_sampled_frame_indices, iter_sampled_video_frames, should_process_frame
from app.services.profile_service import (
    load_camera_optics_profile,
    load_drone_profile,
    load_target_profile,
)


@dataclass(slots=True)
class FramePreview:
    frame_index: int
    timestamp_seconds: float = 0.0
    detections: list[Detection] = field(default_factory=list)
    approved_target: ApprovedTarget | None = None
    tracking: TrackingResult | None = None
    guidance: GuidanceResult | None = None
    guidance_command: GuidanceCommand | None = None
    overlay_lines: list[str] = field(default_factory=list)
    events: list[PipelineEvent] = field(default_factory=list)


@dataclass(slots=True)
class ChunkProcessingResult:
    previews: list[FramePreview]
    approved_target: ApprovedTarget | None
    missed_detection_refreshes: int
    next_frame_index: int
    completed: bool


class PlaceholderPipelineOrchestrator:
    """Deterministic Milestone 1 preview path."""

    def __init__(
        self,
        detector: BaseDetector | None = None,
        tracker: BaseTracker | None = None,
    ) -> None:
        self.detector = detector or PlaceholderDetector()
        self.tracker = tracker or BridgeTracker()

    def build_preview(
        self,
        metadata: VideoMetadata,
        config: ProcessingConfig,
        max_processed_frames: int | None = 6,
    ) -> list[FramePreview]:
        config.validate()
        drone_profile = load_drone_profile(config.drone_profile_id)
        camera_optics_profile = load_camera_optics_profile(config.camera_optics_profile_id)
        target_profile = load_target_profile(config.target_profile_id)

        previews: list[FramePreview] = []
        approved_target: ApprovedTarget | None = None

        for frame_index in iter_sampled_frame_indices(
            frame_count=metadata.frame_count,
            frame_sampling_interval=config.frame_sampling_interval,
        ):
            if max_processed_frames is not None and len(previews) >= max_processed_frames:
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
                approved_target = self.tracker.initialize(
                    target_id="placeholder-target-1",
                    detection=best_detection,
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
            guidance_command: GuidanceCommand | None = None

            if approved_target is not None:
                tracking = self.tracker.track(
                    approved_target=approved_target,
                    frame_index=frame_index,
                )
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
                        drone_profile=drone_profile,
                        camera_profile=camera_optics_profile,
                        target_profile=target_profile,
                    )
                    guidance_command = calculate_guidance_command(
                        guidance=guidance,
                        metadata=metadata,
                        drone_profile=drone_profile,
                        auto_engagement=config.auto_engagement,
                        engagement_distance_threshold_m=config.engagement_distance_threshold_m,
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
                    timestamp_seconds=(frame_index / metadata.fps) if metadata.fps > 0 else 0.0,
                    detections=detections,
                    approved_target=approved_target,
                    tracking=tracking,
                    guidance=guidance,
                    guidance_command=guidance_command,
                    overlay_lines=build_overlay_lines(tracking=tracking, guidance=guidance),
                    events=events,
                )
            )

        return previews

    def build_preview_from_video(
        self,
        video_bytes: bytes,
        metadata: VideoMetadata,
        config: ProcessingConfig,
        filename: str | None = None,
        mime_type: str | None = None,
    ) -> list[FramePreview]:
        config.validate()
        self.tracker = build_tracker_for_config(config)
        drone_profile = load_drone_profile(config.drone_profile_id)
        camera_optics_profile = load_camera_optics_profile(config.camera_optics_profile_id)
        target_profile = load_target_profile(config.target_profile_id)

        previews: list[FramePreview] = []
        approved_target: ApprovedTarget | None = None
        runtime_detector = build_detector_for_config(config)
        target_id = "runtime-target-1"
        missed_detection_refreshes = 0

        for video_frame in iter_sampled_video_frames(
            video_bytes=video_bytes,
            frame_sampling_interval=1,
            filename=filename,
            mime_type=mime_type,
        ):
            events = [
                PipelineEvent(
                    stage="frame_iteration",
                    message="Frame sampled from uploaded video.",
                    frame_index=video_frame.frame_index,
                )
            ]
            detections: list[Detection] = []
            run_detection = should_process_frame(
                frame_index=video_frame.frame_index,
                frame_sampling_interval=config.frame_sampling_interval,
            ) or approved_target is None

            if run_detection:
                detections = runtime_detector.detect(video_frame.frame_index, frame=video_frame.frame)

                if detections:
                    had_target = approved_target is not None
                    best_detection = max(detections, key=lambda detection: detection.confidence)
                    approved_target = (
                        self.tracker.refresh(
                            approved_target=approved_target,
                            detection=best_detection,
                            frame=video_frame.frame,
                        )
                        if had_target and approved_target is not None
                        else self.tracker.initialize(
                            target_id=target_id,
                            detection=best_detection,
                            frame=video_frame.frame,
                        )
                    )
                    missed_detection_refreshes = 0
                    events.append(
                        PipelineEvent(
                            stage="detection",
                            message=(
                                f"{runtime_detector.backend_name} detection accepted on refresh frame "
                                f"with confidence {best_detection.confidence:.2f}."
                            ),
                            frame_index=video_frame.frame_index,
                        )
                    )
                    if had_target:
                        events.append(
                            PipelineEvent(
                                stage="tracking_refresh",
                                message="Tracker anchor refreshed from the latest detection.",
                                frame_index=video_frame.frame_index,
                            )
                        )
                    else:
                        events.append(
                            PipelineEvent(
                                stage="approval",
                                message="Auto-approved the first confident detection and started tracking.",
                                frame_index=video_frame.frame_index,
                            )
                        )
                else:
                    if approved_target is not None:
                        missed_detection_refreshes += 1
                    events.append(
                        PipelineEvent(
                            stage="detection",
                            message="No detection on this refresh frame; tracker retained the last known target.",
                            frame_index=video_frame.frame_index,
                        )
                    )
                    if (
                        approved_target is not None
                        and missed_detection_refreshes > config.tracker_max_missed_refreshes
                    ):
                        approved_target = None
                        self.tracker.reset()
                        events.append(
                            PipelineEvent(
                                stage="tracking_lost",
                                message="Tracking reset after consecutive detector refresh misses.",
                                frame_index=video_frame.frame_index,
                            )
                        )
            else:
                events.append(
                    PipelineEvent(
                        stage="tracking_bridge",
                        message="Detection skipped on this frame; using tracker bridge until the next refresh frame.",
                        frame_index=video_frame.frame_index,
                    )
                )

            tracking: TrackingResult | None = None
            guidance: GuidanceResult | None = None
            guidance_command: GuidanceCommand | None = None

            if approved_target is not None:
                tracking = self.tracker.track(
                    approved_target=approved_target,
                    frame_index=video_frame.frame_index,
                    frame=video_frame.frame,
                )
                events.append(
                    PipelineEvent(
                        stage="tracking",
                        message="Tracker propagated the latest target state through the uploaded video timeline.",
                        frame_index=video_frame.frame_index,
                    )
                )

                if tracking.bbox is not None:
                    guidance = calculate_guidance(
                        frame_index=video_frame.frame_index,
                        metadata=metadata,
                        bbox=tracking.bbox,
                        horizontal_fov_deg=config.horizontal_fov_deg,
                        vertical_fov_deg=config.vertical_fov_deg,
                        drone_profile=drone_profile,
                        camera_profile=camera_optics_profile,
                        target_profile=target_profile,
                    )
                    guidance_command = calculate_guidance_command(
                        guidance=guidance,
                        metadata=metadata,
                        drone_profile=drone_profile,
                        auto_engagement=config.auto_engagement,
                        engagement_distance_threshold_m=config.engagement_distance_threshold_m,
                    )
                    events.append(
                        PipelineEvent(
                            stage="guidance",
                            message="Guidance offsets calculated against the uploaded video frame.",
                            frame_index=video_frame.frame_index,
                        )
                    )

            previews.append(
                FramePreview(
                    frame_index=video_frame.frame_index,
                    timestamp_seconds=video_frame.timestamp_seconds,
                    detections=detections,
                    approved_target=approved_target,
                    tracking=tracking,
                    guidance=guidance,
                    guidance_command=guidance_command,
                    overlay_lines=build_overlay_lines(tracking=tracking, guidance=guidance),
                    events=events,
                )
            )

        return previews

    def build_preview_chunk_from_video_path(
        self,
        *,
        video_path: str,
        metadata: VideoMetadata,
        config: ProcessingConfig,
        start_frame_index: int,
        max_frames: int,
        filename: str | None = None,
        mime_type: str | None = None,
        approved_target: ApprovedTarget | None = None,
        missed_detection_refreshes: int = 0,
        target_id: str = "runtime-target-1",
    ) -> ChunkProcessingResult:
        del filename, mime_type
        config.validate()
        self.tracker = build_tracker_for_config(config)
        drone_profile = load_drone_profile(config.drone_profile_id)
        camera_optics_profile = load_camera_optics_profile(config.camera_optics_profile_id)
        target_profile = load_target_profile(config.target_profile_id)
        if start_frame_index < 0:
            raise ValueError("start_frame_index cannot be negative")
        if max_frames < 1:
            raise ValueError("max_frames must be at least 1")

        previews: list[FramePreview] = []
        runtime_detector = build_detector_for_config(config)
        capture = cv2.VideoCapture(video_path)
        if not capture.isOpened():
            capture.release()
            raise ValueError("Unable to open uploaded video for chunk processing")

        try:
            capture.set(cv2.CAP_PROP_POS_FRAMES, float(start_frame_index))
            next_frame_index = start_frame_index
            processed_frames = 0
            completed = False

            while processed_frames < max_frames:
                ok, frame = capture.read()
                if not ok:
                    completed = True
                    break

                video_frame_index = next_frame_index
                timestamp_seconds = (
                    video_frame_index / metadata.fps if metadata.fps > 0 else 0.0
                )
                events = [
                    PipelineEvent(
                        stage="frame_iteration",
                        message="Frame sampled from uploaded video.",
                        frame_index=video_frame_index,
                    )
                ]
                detections: list[Detection] = []
                run_detection = (
                    approved_target is None
                    or should_process_frame(
                        frame_index=video_frame_index,
                        frame_sampling_interval=config.frame_sampling_interval,
                    )
                )

                if run_detection:
                    detections = runtime_detector.detect(video_frame_index, frame=frame)
                    if detections:
                        had_target = approved_target is not None
                        best_detection = max(detections, key=lambda detection: detection.confidence)
                        approved_target = (
                            self.tracker.refresh(
                                approved_target=approved_target,
                                detection=best_detection,
                                frame=frame,
                            )
                            if had_target and approved_target is not None
                            else self.tracker.initialize(
                                target_id=target_id,
                                detection=best_detection,
                                frame=frame,
                            )
                        )
                        missed_detection_refreshes = 0
                        events.append(
                            PipelineEvent(
                                stage="detection",
                                message=(
                                    f"{runtime_detector.backend_name} detection accepted on refresh frame "
                                    f"with confidence {best_detection.confidence:.2f}."
                                ),
                                frame_index=video_frame_index,
                            )
                        )
                        events.append(
                            PipelineEvent(
                                stage="tracking_refresh" if had_target else "approval",
                                message=(
                                    "Tracker anchor refreshed from the latest detection."
                                    if had_target
                                    else "Auto-approved the first confident detection and started tracking."
                                ),
                                frame_index=video_frame_index,
                            )
                        )
                    else:
                        if approved_target is not None:
                            missed_detection_refreshes += 1
                        events.append(
                            PipelineEvent(
                                stage="detection",
                                message="No detection on this refresh frame; tracker retained the last known target.",
                                frame_index=video_frame_index,
                            )
                        )
                        if (
                            approved_target is not None
                            and missed_detection_refreshes > config.tracker_max_missed_refreshes
                        ):
                            approved_target = None
                            self.tracker.reset()
                            events.append(
                                PipelineEvent(
                                    stage="tracking_lost",
                                    message="Tracking reset after consecutive detector refresh misses.",
                                    frame_index=video_frame_index,
                                )
                            )
                else:
                    events.append(
                        PipelineEvent(
                            stage="tracking_bridge",
                            message="Detection skipped on this frame; using tracker bridge until the next refresh frame.",
                            frame_index=video_frame_index,
                        )
                    )

                tracking: TrackingResult | None = None
                guidance: GuidanceResult | None = None
                guidance_command: GuidanceCommand | None = None

                if approved_target is not None:
                    tracking = self.tracker.track(
                        approved_target=approved_target,
                        frame_index=video_frame_index,
                        frame=frame,
                    )
                    events.append(
                        PipelineEvent(
                            stage="tracking",
                            message="Tracker propagated the latest target state through the uploaded video timeline.",
                            frame_index=video_frame_index,
                        )
                    )

                    if tracking.bbox is not None:
                        guidance = calculate_guidance(
                            frame_index=video_frame_index,
                            metadata=metadata,
                            bbox=tracking.bbox,
                            horizontal_fov_deg=config.horizontal_fov_deg,
                            vertical_fov_deg=config.vertical_fov_deg,
                            drone_profile=drone_profile,
                            camera_profile=camera_optics_profile,
                            target_profile=target_profile,
                        )
                        guidance_command = calculate_guidance_command(
                            guidance=guidance,
                            metadata=metadata,
                            drone_profile=drone_profile,
                            auto_engagement=config.auto_engagement,
                            engagement_distance_threshold_m=config.engagement_distance_threshold_m,
                        )
                        events.append(
                            PipelineEvent(
                                stage="guidance",
                                message="Guidance offsets calculated against the uploaded video frame.",
                                frame_index=video_frame_index,
                            )
                        )

                previews.append(
                    FramePreview(
                        frame_index=video_frame_index,
                        timestamp_seconds=timestamp_seconds,
                        detections=detections,
                        approved_target=approved_target,
                        tracking=tracking,
                        guidance=guidance,
                        guidance_command=guidance_command,
                        overlay_lines=build_overlay_lines(tracking=tracking, guidance=guidance),
                        events=events,
                    )
                )

                next_frame_index += 1
                processed_frames += 1

            if next_frame_index >= metadata.frame_count:
                completed = True
        finally:
            capture.release()

        return ChunkProcessingResult(
            previews=previews,
            approved_target=approved_target,
            missed_detection_refreshes=missed_detection_refreshes,
            next_frame_index=next_frame_index,
            completed=completed,
        )
