from __future__ import annotations

import pytest

from app.services.profile_service import (
    list_camera_optics_profile_ids,
    list_drone_profile_ids,
    load_camera_optics_profile,
    load_drone_profile,
)


def test_list_drone_profile_ids_returns_seed_profiles() -> None:
    profile_ids = list_drone_profile_ids()

    assert "multicopter_center_camera" in profile_ids
    assert "multicopter_offset_camera" in profile_ids
    assert "plane_offset_camera" in profile_ids


def test_load_drone_profile_reads_expected_defaults() -> None:
    profile = load_drone_profile("multicopter_offset_camera")

    assert profile.drone_type == "multicopter"
    assert profile.control_model == "motors"
    assert profile.camera_offset_x_px == 48.0
    assert profile.camera_offset_y_px == -24.0


def test_list_camera_optics_profile_ids_returns_seed_profiles() -> None:
    profile_ids = list_camera_optics_profile_ids()

    assert "standard_rectilinear" in profile_ids
    assert "wide_angle_drone" in profile_ids


def test_load_camera_optics_profile_reads_expected_defaults() -> None:
    profile = load_camera_optics_profile("wide_angle_drone")

    assert profile.lens_model == "opencv_radial_tangential"
    assert profile.horizontal_fov_deg == 120.0
    assert profile.vertical_fov_deg == 80.0
    assert profile.k1 == -0.32
    assert profile.k2 == 0.10


def test_unknown_drone_profile_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_drone_profile("missing_profile")


def test_unknown_camera_optics_profile_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_camera_optics_profile("missing_profile")
