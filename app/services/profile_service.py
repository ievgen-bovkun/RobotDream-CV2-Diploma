from __future__ import annotations

from pathlib import Path
import tomllib

from app.domain.models import CameraOpticsProfile, DroneProfile, TargetProfile


PROFILE_ROOT = Path(__file__).resolve().parents[2] / "configs"
DRONE_PROFILE_DIR = PROFILE_ROOT / "drone_profiles"
CAMERA_PROFILE_DIR = PROFILE_ROOT / "camera_profiles"
TARGET_PROFILE_DIR = PROFILE_ROOT / "target_profiles"


def _load_toml(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def list_drone_profile_ids() -> list[str]:
    return sorted(path.stem for path in DRONE_PROFILE_DIR.glob("*.toml"))


def list_camera_optics_profile_ids() -> list[str]:
    return sorted(path.stem for path in CAMERA_PROFILE_DIR.glob("*.toml"))


def list_target_profile_ids() -> list[str]:
    return sorted(path.stem for path in TARGET_PROFILE_DIR.glob("*.toml"))


def load_drone_profile(profile_id: str) -> DroneProfile:
    path = DRONE_PROFILE_DIR / f"{profile_id}.toml"
    if not path.exists():
        raise FileNotFoundError(f"Unknown drone profile: {profile_id}")

    raw = _load_toml(path)
    profile = DroneProfile(
        profile_id=str(raw["profile_id"]),
        label=str(raw["label"]),
        drone_type=str(raw["drone_type"]),
        camera_offset_x_px=float(raw.get("camera_offset_x_px", 0.0)),
        camera_offset_y_px=float(raw.get("camera_offset_y_px", 0.0)),
        control_model=str(raw["control_model"]),
        max_yaw_command_norm=float(raw.get("max_yaw_command_norm", 1.0)),
        max_pitch_command_norm=float(raw.get("max_pitch_command_norm", 1.0)),
    )
    profile.validate()
    return profile


def load_target_profile(profile_id: str) -> TargetProfile:
    path = TARGET_PROFILE_DIR / f"{profile_id}.toml"
    if not path.exists():
        raise FileNotFoundError(f"Unknown target profile: {profile_id}")

    raw = _load_toml(path)
    profile = TargetProfile(
        profile_id=str(raw["profile_id"]),
        label=str(raw["label"]),
        wingspan_m=float(raw["wingspan_m"]),
        length_m=float(raw["length_m"]),
        cruise_speed_kmh=float(raw["cruise_speed_kmh"]),
        average_speed_kmh=float(raw["average_speed_kmh"]),
        notes=str(raw.get("notes", "")),
    )
    profile.validate()
    return profile


def load_camera_optics_profile(profile_id: str) -> CameraOpticsProfile:
    path = CAMERA_PROFILE_DIR / f"{profile_id}.toml"
    if not path.exists():
        raise FileNotFoundError(f"Unknown camera optics profile: {profile_id}")

    raw = _load_toml(path)
    profile = CameraOpticsProfile(
        profile_id=str(raw["profile_id"]),
        label=str(raw["label"]),
        lens_model=str(raw["lens_model"]),
        horizontal_fov_deg=float(raw["horizontal_fov_deg"]),
        vertical_fov_deg=float(raw["vertical_fov_deg"]),
        k1=float(raw.get("k1", 0.0)),
        k2=float(raw.get("k2", 0.0)),
        p1=float(raw.get("p1", 0.0)),
        p2=float(raw.get("p2", 0.0)),
        k3=float(raw.get("k3", 0.0)),
    )
    profile.validate()
    return profile
