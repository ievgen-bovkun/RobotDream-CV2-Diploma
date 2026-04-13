# Milestone Roadmap

## Status Summary

- Milestone 1: completed, repository foundation and typed contracts are in place
- Milestone 2: completed, uploaded video handling and metadata extraction are working in the app
- Milestone 3: completed, frame iteration and runtime chunk processing are wired into the UI
- Milestone 4: completed, real YOLO baseline detection is integrated and benchmarked across the current daylight clips, with the latest baseline captured in `docs/decisions/benchmark-log-2026-04-12.md`
- Milestone 5: pending, manual target approval workflow is not implemented yet
- Milestone 6: in progress, bridge tracking, detector-refresh tuning, and tracker-hold defaults exist, but tracking still relies on a placeholder tracker and the rear-view hard case remains weak
- Milestone 7: in progress, guidance math, runtime synchronization, and on-video overlays are wired into the Streamlit baseline, but the operator flow is still incomplete
- Milestone 8: pending, export target naming and structured-log scaffolding exist, but there is no completed end-to-end export flow in the app yet
- Milestone 9: in progress, deterministic unit and integration tests exist, but local `pytest` collection is currently broken because the repo does not yet expose the `app` package on the test import path

## Delivery Rule

Each milestone should remain independently runnable, visibly testable, and small enough to validate before broadening scope.

## Backlog Focus

- Add adaptive detector refresh so the pipeline can lower the sampling interval automatically when bbox size grows fast, confidence drops, or the scene becomes unstable.
- Add camera-profile-aware runtime presets so daylight RGB and thermal clips start with different YOLO and open-vocabulary prompt parameters.
- Replace the current bridge tracker with an image-aware tracker so close-up targets keep scaling correctly instead of holding a stale bbox.
- Add manual operator approval before long-running tracking so Milestone 5 matches the original product flow.
- Fix local `pytest` collection by exposing the repo `app` package to the test runner, then restore a green baseline for regression safety.
- Split runtime progress into `video frame`, `displayed pipeline frame`, and `processed up to` so the UI never suggests the pipeline is ahead of the video.
- Add device-specific acceleration profiles after the baseline tracker is stable:
  - `Apple Silicon / M4 Pro` via `PyTorch MPS` on Metal
  - `AMD Radeon RX 7900 XTX` via `ROCm`
  - `NVIDIA Jetson Orin Nano` via `JetPack CUDA/TensorRT`
  - `Raspberry Pi 5 AI HAT+` via the on-board `Hailo NPU`
- Add a dedicated `GPU Acceleration and Device Profiles` milestone slice for benchmarking latency, supported backends, and model/export constraints on each target device.
- Add fine-tuning for the detection model so daylight, thermal, rear-view, and hard-case clips can move beyond the generic baseline.
- Add tracking-model evaluation and tuning so the project can move from the current bridge tracker toward a stronger image-aware or learned tracker once the guidance workflow is stable.
