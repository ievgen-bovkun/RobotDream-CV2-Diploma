# Benchmark Log — 2026-04-12

This file records intermediate detector and tracking benchmark results so the project keeps a visible research trail inside the repository.

## Scope

- Detector backend: `YOLO` (`yolo11n.pt`) unless noted otherwise
- Runtime mode: detector refresh every `N` frames with bridge tracking between refreshes
- Camera profile: `daylight`
- Goal of this pass: keep a practical GUI-ready daylight baseline while separating hard-case clips for later work

## Photo Baseline

### `test-photos/` RGB screenshots

| Backend | Result | Notes |
| --- | ---: | --- |
| `YOLO` | `9 / 11` hits | Good baseline, two misses remained |
| `YOLOWorld` | `10 / 11` hits | Better zero-label photo result than plain YOLO |

### Current takeaway

- `YOLOWorld` is stronger for photo-only benchmarking.
- `YOLO` remains the simpler runtime/video baseline for the Streamlit app.

## Video Baseline

### Daylight clip: `test-videos/daytime-color-shahed-boom-zoom.MP4`

Current sweep focused on improving precision while preserving early lock-on.

| Threshold | Frame Interval | Processed Frames | Detection Frames | First Detection | Last Detection | Tracking Frames | Notes |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `0.45` | `3` | `455` | `79` | `0` | `243` | `249` | Most permissive working baseline in this sweep |
| `0.50` | `3` | `455` | `78` | `0` | `243` | `246` | Slightly cleaner than `0.45`, minimal loss |
| `0.55` | `3` | `455` | `76` | `0` | `243` | `242` | Best higher-confidence candidate after full daylight validation |
| `0.60` | `3` | `455` | `72` | `4` | `243` | `235` | Still workable, but starts losing immediate lock-on and some coverage |
| `0.70` | `3` | `455` | `55` | `8` | `210` | `187` | Too aggressive for this clip, noticeable loss in stability |

### Working conclusion for `boom-zoom`

- The current best practical baseline is `0.55 / 3` after full daylight validation.
- `0.45 / 3` is still a useful fallback when we want maximum recall.
- `0.55 / 3` is the strongest higher-threshold candidate that still keeps immediate frame-`0` acquisition on the `boom-zoom` clip.
- `0.60 / 3` is usable, but it already delays first detection to frame `4`.
- `0.70 / 3` is too strict for the current detector/tracker stack on this clip.

## Cross-Daylight Validation for Higher Confidence

The `0.55 / 3` candidate was compared against the old default `0.45 / 3` across all current daylight clips.

| Video | Baseline `0.45 / 3` Tracking | Candidate `0.55 / 3` Tracking | Tracking Change | Result |
| --- | ---: | ---: | ---: | --- |
| `daytime-color-shahed-boom-zoom.MP4` | `249` | `242` | `-2.8%` | Pass |
| `daytime-color-shahed.MP4` | `170` | `139` | `-18.2%` | Pass |
| `daytime-color-shahed-from-behind.mp4` | `11` | `11` | `0.0%` | Pass |

### Default-setting decision

- The higher-confidence candidate `0.55 / 3` stays within the allowed `20%` tracking drop on all current daylight clips.
- Because of that, `0.55 / 3` becomes the default value for the GUI and pipeline.
- The main loss with higher confidence is not only in extreme close-up. On `daytime-color-shahed.MP4`, first detection moved from frame `4` to frame `17`, so some loss already happens in earlier, weaker-visibility phases.

## Current Daylight Baseline Sweep

Current baseline setting:

- detector backend: `YOLO`
- camera profile: `daylight`
- threshold: `0.55`
- requested frame interval: `3`

All current daytime clips were re-checked with the baseline setting above.

| Video | FPS | Frames | Detection Frames | First Detection | Last Detection | Tracking Frames | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `daytime-color-drones-mashup.MP4` | `30.00` | `463` | `24` | `210` | `318` | `82` | Mixed-drone mashup, target acquisition starts later in the sequence |
| `daytime-color-shahed-boom-zoom.MP4` | `30.00` | `455` | `76` | `0` | `243` | `242` | Best GUI baseline clip |
| `daytime-color-shahed-from-behihd-2.MP4` | `30.00` | `580` | `59` | `313` | `562` | `204` | Much healthier rear-view result than the original hard case |
| `daytime-color-shahed.MP4` | `30.00` | `227` | `43` | `17` | `177` | `139` | Stable daylight clip with moderate delay before first lock |
| `daytime-color-shahed-from-behind.mp4` | `23.98` | `548` | `2` | `403` | `408` | `11` | Original hard case, detections arrive very late and only briefly |

### Why `from-behind` looked like “no detections” in the UI

- The current benchmark still finds only `2` detector hits on `daytime-color-shahed-from-behind.mp4`.
- Those hits happen at frames `403` and `408`, which is around `16.8s` into a `22.9s` clip.
- The tracking window is only `11` frames total, which is about `0.46s` at `23.98 FPS`.
- That means the terminal can honestly report `2 detections`, while the GUI can still feel like “nothing was detected” because the visible bbox appears very late and only for a short moment.

## Tracker Hold Quick Win

The tracker-hold window was tested as a low-risk tuning knob before committing the current step.

| Video | Threshold | Interval | Hold After Missed Detections | Detection Frames | Tracking Frames | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `daytime-color-shahed-from-behind.mp4` | `0.55` | `3` | `1` | `2` | `11` | Original aggressive reset behavior |
| `daytime-color-shahed-from-behind.mp4` | `0.55` | `3` | `3` | `2` | `17` | Quick win: same detections, longer post-detection tracking |
| `daytime-color-shahed-boom-zoom.MP4` | `0.55` | `3` | `1` | `76` | `242` | Previous working baseline |
| `daytime-color-shahed-boom-zoom.MP4` | `0.55` | `3` | `3` | `74` | `255` | Better tracking continuity with no meaningful detection regression |

### Tracker hold decision

- `tracker_max_missed_refreshes = 3` is now the recommended default.
- It is not enough to solve the original `from-behind` hard case, but it extends the useful tracking tail without hurting the strongest daylight baseline.

## Hard Case

### Daylight clip: `test-videos/daytime-color-shahed-from-behind.mp4`

Known hard case for the current runtime architecture.

| Threshold | Frame Interval | Detection Frames | First Detection | Tracking Frames | Notes |
| ---: | ---: | ---: | ---: | ---: | --- |
| `0.70` | `10` | `0` | `—` | `0` | Too strict, no useful runtime detection |
| `0.55` | `3` | `2` | `403` | `11` | Same very late acquisition under the current stricter reset logic |
| `0.45` | `3` | `2` | `403` | `11` | Lowering threshold did not materially improve this clip in the current pipeline state |

### Current takeaway

- `from-behind` should stay in the backlog as a hard-case clip.
- It likely needs either:
  - adaptive detector refresh,
  - a real image-aware tracker,
  - or a detector better tuned for that rear/close-up regime.

## Preset Direction

The benchmark direction now separates two practical daylight modes:

- `GUI baseline`
  - target clip: `daytime-color-shahed-boom-zoom.MP4`
  - default preset: `threshold = 0.55`, `frame_sampling_interval = 3`
- `Hard-case research`
  - target clip: `daytime-color-shahed-from-behind.mp4`
  - remains open for future optimization

## Notes

- These numbers are intermediate research artifacts, not final acceptance metrics.
- As the tracker and detector-refresh logic evolve, repeated runs may change the totals.
- New benchmark rows should be appended instead of replacing the older observations, so progress stays visible over time.
