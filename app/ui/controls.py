from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from app.domain.config import (
    ProcessingConfig,
    SUPPORTED_DETECTOR_DEVICES,
    SUPPORTED_CAMERA_PROFILES,
    get_camera_profile_preset,
    get_supported_input_sizes,
)
from app.services.profile_service import (
    list_camera_optics_profile_ids,
    list_drone_profile_ids,
    load_camera_optics_profile,
    load_drone_profile,
    load_target_profile,
)


@dataclass(slots=True, frozen=True)
class UiActions:
    start_processing: bool
    reset_state: bool
    tactical_pause: bool = False
    toggle_guidance: bool = False


def _format_camera_profile(camera_profile: str) -> str:
    return "Daylight RGB" if camera_profile == "daylight" else "Thermal"


def _format_detector_device(device: str) -> str:
    labels = {
        "auto": "Auto",
        "cpu": "CPU",
        "mps": "Metal (MPS)",
    }
    return labels.get(device, device)


def render_detection_settings() -> ProcessingConfig:
    base_defaults = ProcessingConfig()
    drone_profile_ids = list_drone_profile_ids()
    camera_optics_profile_ids = list_camera_optics_profile_ids()
    drone_profile_map = {profile_id: load_drone_profile(profile_id) for profile_id in drone_profile_ids}
    optics_profile_map = {
        profile_id: load_camera_optics_profile(profile_id) for profile_id in camera_optics_profile_ids
    }
    target_profile = load_target_profile(base_defaults.target_profile_id)

    with st.expander("Detection Settings", expanded=True):
        st.caption(
            "Tune the runtime thresholding and output behavior here. These settings stay wired to the typed config model."
        )

        top_profiles = st.columns(3)
        selected_camera_profile = top_profiles[0].segmented_control(
            "Camera profile",
            options=list(SUPPORTED_CAMERA_PROFILES),
            default=base_defaults.camera_profile,
            format_func=_format_camera_profile,
            width="stretch",
            help="Switch between daylight RGB and thermal detector presets.",
        )
        camera_profile = str(selected_camera_profile or base_defaults.camera_profile)
        selected_drone_profile = top_profiles[1].segmented_control(
            "Drone profile",
            options=drone_profile_ids,
            default=base_defaults.drone_profile_id,
            format_func=lambda profile_id: drone_profile_map[profile_id].label,
            width="stretch",
            help="Defines drone type, control model, and camera mount offset relative to the drone center.",
        )
        drone_profile_id = str(selected_drone_profile or base_defaults.drone_profile_id)
        selected_camera_optics_profile = top_profiles[2].segmented_control(
            "Camera optics profile",
            options=camera_optics_profile_ids,
            default=base_defaults.camera_optics_profile_id,
            format_func=lambda profile_id: optics_profile_map[profile_id].label,
            width="stretch",
            help="Defines lens behavior such as rectilinear, wide-angle, or fisheye-like distortion.",
        )
        camera_optics_profile_id = str(
            selected_camera_optics_profile or base_defaults.camera_optics_profile_id
        )

        defaults = ProcessingConfig(
            camera_profile=camera_profile,
            drone_profile_id=drone_profile_id,
            camera_optics_profile_id=camera_optics_profile_id,
        )
        profile_preset = get_camera_profile_preset(camera_profile)
        supported_input_sizes = get_supported_input_sizes(camera_profile)
        selected_drone_profile_model = drone_profile_map[drone_profile_id]
        selected_camera_optics_model = optics_profile_map[camera_optics_profile_id]
        st.caption(
            "Preset detector backend hints: "
            f"imgsz={profile_preset['input_size']}, "
            f"nms_iou={profile_preset['nms_iou_threshold']}, "
            f"max_det={profile_preset['max_detections']}, "
            f"prompt_profile={len(profile_preset['prompt_terms'])} terms."
        )
        st.caption(
            "Guidance profiles: "
            f"drone_offset=({selected_drone_profile_model.camera_offset_x_px:.0f}px, "
            f"{selected_drone_profile_model.camera_offset_y_px:.0f}px), "
            f"control={selected_drone_profile_model.control_model}, "
            f"lens={selected_camera_optics_model.lens_model}, "
            f"target={target_profile.label}."
        )

        top_row = st.columns(2)
        detection_threshold = top_row[0].slider(
            "Detection confidence threshold",
            min_value=0.1,
            max_value=1.0,
            value=float(defaults.detection_threshold),
            step=0.05,
        )
        frame_sampling_interval = top_row[1].number_input(
            "Frame sampling interval",
            min_value=1,
            max_value=60,
            value=int(defaults.frame_sampling_interval),
            step=1,
            help="Run detector on every Nth frame and use tracking on the frames in between.",
        )
        mid_row = st.columns(2)
        input_size = mid_row[0].segmented_control(
            "Detector input size",
            options=list(supported_input_sizes),
            default=int(defaults.input_size),
            width="stretch",
            help="Smaller sizes preprocess faster; larger sizes keep more detail for hard detections.",
        )
        detector_device = mid_row[1].segmented_control(
            "Detector device",
            options=list(SUPPORTED_DETECTOR_DEVICES),
            default=defaults.detector_device,
            format_func=_format_detector_device,
            width="stretch",
            help="Auto tries Metal first on Apple Silicon and falls back to CPU if unavailable.",
        )
        lower_row = st.columns(2)
        tracker_max_missed_refreshes = lower_row[0].number_input(
            "Tracker hold after missed detections",
            min_value=0,
            max_value=12,
            value=int(defaults.tracker_max_missed_refreshes),
            step=1,
            help="Keep the current track alive for this many detector refresh misses before resetting it.",
        )
        st.caption(
            f"Target profile locked for now: {target_profile.label}. Device default: {_format_detector_device(str(detector_device or defaults.detector_device))}."
        )

        bottom_row = st.columns(3)
        save_output_video = bottom_row[0].checkbox("Save annotated video", value=False)
        save_logs = bottom_row[1].checkbox("Save structured logs", value=True)
        debug_mode = bottom_row[2].checkbox("Debug mode", value=True)
        auto_engagement = st.checkbox(
            "Auto engagement",
            value=bool(base_defaults.auto_engagement),
            help="If enabled, guidance marks the target as neutralized when estimated range reaches 2 meters or less.",
        )

    config = ProcessingConfig(
        camera_profile=camera_profile,
        drone_profile_id=drone_profile_id,
        camera_optics_profile_id=camera_optics_profile_id,
        target_profile_id=base_defaults.target_profile_id,
        detection_threshold=detection_threshold,
        frame_sampling_interval=int(frame_sampling_interval),
        detector_device=str(detector_device or defaults.detector_device),
        input_size=int(input_size or defaults.input_size),
        tracker_max_missed_refreshes=int(tracker_max_missed_refreshes),
        auto_engagement=bool(auto_engagement),
        engagement_distance_threshold_m=float(base_defaults.engagement_distance_threshold_m),
        horizontal_fov_deg=float(selected_camera_optics_model.horizontal_fov_deg),
        vertical_fov_deg=float(selected_camera_optics_model.vertical_fov_deg),
        save_output_video=save_output_video,
        save_logs=save_logs,
        debug_mode=debug_mode,
    )
    config.validate()
    return config
