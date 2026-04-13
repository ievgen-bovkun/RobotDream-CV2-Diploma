# Guidance Session Note — 2026-04-13

This note captures the current technical context for the next implementation session so work can resume quickly on any machine.

## Environment

- Active Python baseline: `3.11.1`
- Pinned PyTorch stack for the repo:
  - `torch==2.5.1`
  - `torchvision==0.20.1`
- Reason for pinning:
  - the previous environment had `torch==2.11.0` and `torchvision==0.26.0`
  - that pair looked suspicious for the current project and was replaced with a stable Python 3.11 pair

## Metal / MPS Status

- `torch.backends.mps.is_built() == True`
- `torch.backends.mps.is_available() == False`
- direct tensor allocation on `device="mps"` still fails even after moving to `torch==2.5.1`
- conclusion:
  - Metal acceleration is **not** working yet in the current environment
  - this should be handled as a separate investigation task, not mixed into the next guidance implementation slice

## Guidance Design Decisions

- `DroneProfile` and `CameraProfile` are separate concerns.
- Guidance math should use an `aim_point`, not the raw geometric frame center.
- `aim_point` should be calculated as:
  - `frame_center + camera_offset`
- `camera_offset_x_px` and `camera_offset_y_px` are offsets relative to the geometric center of the frame, not the top-left corner.
- Built-in reticles already present in test videos should be treated as visual artifacts only and should **not** drive the math.

## Planned Drone Profiles

- `multicopter_center_camera`
- `multicopter_offset_camera`
- `plane_offset_camera`

## Planned Camera Profiles

- `standard_rectilinear`
- `wide_angle_drone`

For the first wide-angle baseline, use a practical OpenCV-style radial/tangential distortion model rather than a brand-specific camera calibration.

## Visual State Plan

- `Detection only`
  - one bbox color
- `Capture confirmation`
  - bright blinking bbox for lock feedback
- `Active tracking + guidance`
  - third bbox color so the operator can instantly read the state

The state indication should not rely on color alone. Use color plus line weight / blink / halo so the overlays remain readable in daylight and thermal footage.

## Overlay Ideas Worth Building Next

- A thin correction line from `aim_point` to target center during active guidance
- Perspective-like corridor rails that point from the drone view toward the target without covering the target itself
- A side-panel signal emulator, likely as:
  - a `guidance ball` inside a circle
  - plus simple yaw / pitch command bars

## Recommended Next Slice

1. Add typed `DroneProfile` and `CameraProfile` models plus simple file-based loading.
2. Add UI selectors for drone and camera profiles.
3. Change guidance math from `frame_center` to `aim_point`.
4. Add three bbox visual states: detection, capture confirmation, active guidance.
5. Add the first signal-emulator panel.

## Non-goals for the Next Slice

- no real ArduPilot integration yet
- no full-frame undistortion pipeline yet
- no continued MPS debugging during the guidance implementation block
