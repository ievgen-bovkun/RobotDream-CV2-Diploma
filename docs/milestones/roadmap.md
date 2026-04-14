# Milestone Roadmap

## Status Summary

- Milestone 1: completed, repository foundation and typed contracts are in place
- Milestone 2: completed, uploaded video handling and metadata extraction are working in the app
- Milestone 3: completed, frame iteration and runtime chunk processing are wired into the UI
- Milestone 4: completed, real YOLO baseline detection is integrated and benchmarked on daytime clips
- Milestone 5: in progress, operator-go exists via `Start Tracking`, but explicit target approval and future target selection workflow are not implemented yet
- Milestone 6: in progress, bridge tracking and detector refresh logic exist but need stronger tracker semantics
- Milestone 7: in progress, guidance overlays, target profiles, distance proxy, and control-signal emulation exist in advanced prototype form
- Milestone 8: pending, export and logs
- Milestone 9: pending, hardening and regression safety

## Delivery Rule

Each milestone should remain independently runnable, visibly testable, and small enough to validate before broadening scope.

## Backlog Focus

- Add adaptive detector refresh so the pipeline can lower the sampling interval automatically when bbox size grows fast, confidence drops, or the scene becomes unstable.
- Add camera-profile-aware runtime presets so daylight RGB and thermal clips start with different YOLO and open-vocabulary prompt parameters.
- Replace the current bridge tracker with an image-aware tracker so close-up targets keep scaling correctly instead of holding a stale bbox.
- Add explicit operator approval and target-selection workflow so Milestone 5 can evolve from the current single-target `Start Tracking` gate into a real approval step for one or many candidates.
- Split runtime progress into `video frame`, `displayed pipeline frame`, and `processed up to` so the UI never suggests the pipeline is ahead of the video.
- Add device-specific acceleration profiles after the baseline tracker is stable:
  - `Apple Silicon / M4 Pro` via `PyTorch MPS` on Metal
  - `AMD Radeon RX 7900 XTX` via `ROCm`
  - `NVIDIA Jetson Orin Nano` via `JetPack CUDA/TensorRT`
  - `Raspberry Pi 5 AI HAT+` via the on-board `Hailo NPU`
- Add a dedicated `GPU Acceleration and Device Profiles` milestone slice for benchmarking latency, supported backends, and model/export constraints on each target device.
- Add thermal-video detector tuning and benchmark coverage as a first-class milestone slice rather than keeping it as a secondary preset only.
- Improve detector quality on the full test-video set until the project reaches `>70%` useful detection coverage on all current reference clips.
- Add mocked drone-guidance output modes for `multicopter` and `plane` profiles with distinct visual feedback in the UI.
- Add on-flight / in-motion video processing as a later milestone after preprocessing-mode guidance is stable.
- Add drone-type classification and target profile matching so the pipeline can switch from the current fixed `Shahed-136` assumption to per-target guidance characteristics.
- Add mashup-video handling so the pipeline can detect when the target drone type changes and update the active target profile accordingly.
- Add multi-drone detection and operator selection so one target can be chosen for guidance when multiple candidates are visible.
- Add fine-tuning for the detection model so daylight, thermal, rear-view, and hard-case clips can move beyond the generic baseline.
- Add tracking-model evaluation and tuning so the project can move from the current bridge tracker toward a stronger image-aware or learned tracker once the guidance workflow is stable.
