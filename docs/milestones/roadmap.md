# Milestone Roadmap

## Status Summary

- Milestone 1: completed, repository foundation and typed contracts are in place
- Milestone 2: completed, uploaded video handling and metadata extraction are working in the app
- Milestone 3: completed, frame iteration and runtime chunk processing are wired into the UI
- Milestone 4: completed, real YOLO baseline detection is integrated and benchmarked on daytime clips
- Milestone 5: pending, manual target approval workflow is not implemented yet
- Milestone 6: in progress, bridge tracking and detector refresh logic exist but need stronger tracker semantics
- Milestone 7: in progress, guidance math and on-video overlays exist in baseline form
- Milestone 8: pending, export and logs
- Milestone 9: pending, hardening and regression safety

## Delivery Rule

Each milestone should remain independently runnable, visibly testable, and small enough to validate before broadening scope.

## Backlog Focus

- Add adaptive detector refresh so the pipeline can lower the sampling interval automatically when bbox size grows fast, confidence drops, or the scene becomes unstable.
- Add camera-profile-aware runtime presets so daylight RGB and thermal clips start with different YOLO and open-vocabulary prompt parameters.
- Replace the current bridge tracker with an image-aware tracker so close-up targets keep scaling correctly instead of holding a stale bbox.
- Add manual operator approval before long-running tracking so Milestone 5 matches the original product flow.
- Split runtime progress into `video frame`, `displayed pipeline frame`, and `processed up to` so the UI never suggests the pipeline is ahead of the video.
