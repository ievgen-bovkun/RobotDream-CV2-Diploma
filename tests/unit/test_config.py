from __future__ import annotations

import pytest

from app.domain.config import ProcessingConfig


def test_processing_config_defaults_are_valid() -> None:
    config = ProcessingConfig()
    config.validate()
    assert config.camera_profile == "daylight"
    assert config.drone_profile_id == "multicopter_center_camera"
    assert config.camera_optics_profile_id == "standard_rectilinear"
    assert config.target_profile_id == "shahed_136"
    assert config.detection_threshold == 0.55
    assert config.frame_sampling_interval == 3
    assert config.tracker_max_missed_refreshes == 3
    assert config.auto_engagement is False
    assert config.engagement_distance_threshold_m == 2.0
    assert config.detector_backend == "open_vocab"
    assert config.detector_device == "auto"
    assert config.input_size == 960
    assert config.nms_iou_threshold == 0.5
    assert config.max_detections == 3
    assert "fixed-wing UAV" in config.prompt_terms
    assert "rear view of flying wing drone" in config.prompt_terms
    assert "loitering munition" in config.prompt_terms


def test_processing_config_thermal_profile_resolves_thermal_presets() -> None:
    config = ProcessingConfig(camera_profile="thermal")

    config.validate()

    assert config.input_size == 1536
    assert config.nms_iou_threshold == 0.45
    assert config.max_detections == 5
    assert any("thermal" in prompt.lower() for prompt in config.prompt_terms)


def test_processing_config_rejects_invalid_threshold() -> None:
    config = ProcessingConfig(detection_threshold=1.2)

    with pytest.raises(ValueError):
        config.validate()


def test_processing_config_rejects_invalid_max_detections() -> None:
    config = ProcessingConfig(max_detections=0)

    with pytest.raises(ValueError):
        config.validate()


def test_processing_config_rejects_negative_tracker_hold() -> None:
    config = ProcessingConfig(tracker_max_missed_refreshes=-1)

    with pytest.raises(ValueError):
        config.validate()


def test_processing_config_rejects_non_positive_engagement_distance() -> None:
    config = ProcessingConfig(engagement_distance_threshold_m=0.0)

    with pytest.raises(ValueError):
        config.validate()


def test_processing_config_rejects_invalid_camera_profile() -> None:
    with pytest.raises(ValueError):
        ProcessingConfig(camera_profile="night_vision")


def test_processing_config_rejects_blank_drone_profile_id() -> None:
    config = ProcessingConfig(drone_profile_id=" ")

    with pytest.raises(ValueError):
        config.validate()


def test_processing_config_rejects_blank_camera_optics_profile_id() -> None:
    config = ProcessingConfig(camera_optics_profile_id=" ")

    with pytest.raises(ValueError):
        config.validate()


def test_processing_config_rejects_blank_target_profile_id() -> None:
    config = ProcessingConfig(target_profile_id=" ")

    with pytest.raises(ValueError):
        config.validate()


def test_processing_config_rejects_invalid_detector_device() -> None:
    config = ProcessingConfig(detector_device="cuda")

    with pytest.raises(ValueError):
        config.validate()
