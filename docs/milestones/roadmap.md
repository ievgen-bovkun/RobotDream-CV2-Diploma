# Milestone Roadmap

## Status Summary

- Milestone 1: completed, repository foundation and typed contracts are in place
- Milestone 2: completed, uploaded video handling and metadata extraction are working in the app
- Milestone 3: completed, preprocessing-based video iteration is wired into the UI and starts immediately after upload
- Milestone 4: completed, real detector integration is working with `open_vocab` daylight defaults, thermal baseline coverage, and Apple Silicon MPS acceleration
- Milestone 5: completed for the single-target demo flow via `Start Tracking`; future explicit candidate approval remains backlog for multi-target scenes
- Milestone 6: completed for the demo slice with bridge tracking, detector refresh logic, confidence-based stale-track cutoff, and optional `CSRT` experimental backend
- Milestone 7: completed for the demo slice with guidance overlays, drone/camera/target profiles, camera-offset aim point, distance proxy, and mocked control-signal emulation
- Milestone 8: pending, export and logs
- Milestone 9: pending, hardening and regression safety
- Acceleration slice: completed for `Apple Silicon / MPS` baseline on `Python 3.13 + torch 2.11.0`, with preprocessing benchmarks captured for `768 / 960 / 1280`
- Thermal slice: completed as a presentation baseline with `open_vocab` runs benchmarked on all current thermal reference clips

## Delivery Rule

Each milestone should remain independently runnable, visibly testable, and small enough to validate before broadening scope.

## Backlog Focus

- Add bbox plausibility guards on detector refresh so overly large background regions cannot silently re-lock the bridge tracker.
- Add adaptive detector refresh so the pipeline can lower the sampling interval automatically when bbox size grows fast, confidence drops, or the scene becomes unstable.
- Add camera-profile-aware runtime presets so daylight RGB and thermal clips start with different YOLO and open-vocabulary prompt parameters.
- Continue evaluating image-aware tracking so the experimental `CSRT` path can mature into a stronger replacement for the current bridge default.
- Add explicit operator approval and target-selection workflow so Milestone 5 can evolve from the current single-target `Start Tracking` gate into a real approval step for one or many candidates.
- Split runtime progress into `video frame`, `displayed pipeline frame`, and `processed up to` so the UI never suggests the pipeline is ahead of the video.
- Add device-specific acceleration profiles after the baseline tracker is stable:
  - `Apple Silicon / M4 Pro` via `PyTorch MPS` on Metal: completed baseline enablement and preprocessing benchmark coverage
  - `AMD Radeon RX 7900 XTX` via `ROCm`
  - `NVIDIA Jetson Orin Nano` via `JetPack CUDA/TensorRT`
  - `Raspberry Pi 5 AI HAT+` via the on-board `Hailo NPU`
- Add a dedicated `GPU Acceleration and Device Profiles` milestone slice for benchmarking latency, supported backends, and model/export constraints on each target device.
- Extend thermal-video tuning beyond the current benchmarked demo baseline and improve target quality on the hardest thermal clips.
- Improve detector quality on the full test-video set until the project reaches `>70%` useful detection coverage on all current reference clips.
- Add mocked drone-guidance output modes for `multicopter` and `plane` profiles with distinct visual feedback in the UI.
- Add on-flight / in-motion video processing as a later milestone after preprocessing-mode guidance is stable.
- Add drone-type classification and target profile matching so the pipeline can switch from the current fixed `Shahed-136` assumption to per-target guidance characteristics.
- Add mashup-video handling so the pipeline can detect when the target drone type changes and update the active target profile accordingly.
- Add multi-drone detection and operator selection so one target can be chosen for guidance when multiple candidates are visible.
- Add fine-tuning for the detection model so daylight, thermal, rear-view, and hard-case clips can move beyond the generic baseline.
- Add tracking-model evaluation and tuning so the project can move from the current bridge tracker toward a stronger image-aware or learned tracker once the guidance workflow is stable.
