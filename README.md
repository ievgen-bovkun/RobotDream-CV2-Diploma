# Drone Detection, Approval, Tracking, and Guidance Demo

This repository contains a diploma-project MVP built with Streamlit and a modular computer-vision pipeline. The current codebase is in a presentation-ready state for prerecorded video detection, tracking, and guidance demos.

It processes prerecorded drone video to detect another drone in the field of view, confirm the target, track it, and generate simple visual guidance. The architecture is intentionally structured so the MVP can later be extended toward broader drone guidance tasks.

## Current Status

- Completed demo milestones:
  - `Milestone 1` foundation and typed contracts
  - `Milestone 2` uploaded video handling and metadata extraction
  - `Milestone 3` preprocessing-based playback flow
  - `Milestone 4` detector integration, daylight tuning, thermal baseline, and Apple Silicon MPS acceleration
  - `Milestone 5` single-target operator-go flow via `Start Tracking`
  - `Milestone 6` bridge tracking with detector refresh and confidence-based stale-track cutoff
  - `Milestone 7` guidance overlays, target/drone/camera profiles, camera-offset aim point, distance proxy, and mocked control-signal visualization
- Experimental slice:
  - `CSRT` tracker backend is available for comparison in the UI, but `Bridge` remains the safer demo default
- Research log: see [`docs/decisions/benchmark-log-2026-04-12.md`](docs/decisions/benchmark-log-2026-04-12.md) for current detector/video benchmark results and working runtime presets

## Shared Project Settings

The repository-level file [`pyproject.toml`](pyproject.toml) is the shared project descriptor for both your Mac and PC. It stores:

- core project metadata
- default processing settings
- repo-relative directories for docs, tests, outputs, and the Streamlit entrypoint
- portability guidance so no machine-specific absolute paths need to be committed

As long as both machines clone the same repository and run commands from the repo root, the same setup should work on macOS and Windows.

## Project Layout

```text
project_root/
  app/
    app.py
    ui/
    pipeline/
    domain/
    services/
    utils/
  tests/
    unit/
    integration/
    fixtures/
  docs/
    specs/
    milestones/
    decisions/
  outputs/
  requirements.txt
  pyproject.toml
  README.md
```

## Quick Start

### macOS / Linux

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app/app.py
```

### Windows PowerShell

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app/app.py
```

## Tests

```bash
pytest
```

The current tests focus on deterministic logic that should remain stable as the project grows:

- config validation
- frame sampling logic
- guidance geometry math
- runtime chunk orchestration and UI state helpers

For stable local behavior on Apple Silicon, use [`.venv-313`](/Users/i.bovkun/PycharmProjects/DroneTracking/.venv-313) with Python `3.13` and the current PyTorch `MPS` stack. Avoid Python `3.14` for this project because it has already caused environment mismatches with detection dependencies.

## Milestone Workflow

For each milestone:

1. Write or update the spec in [`docs/specs/`](docs/specs/).
2. Implement the smallest working slice.
3. Validate manually in the Streamlit app.
4. Add or update automated tests.
5. Record important decisions and limitations in docs.

## What the App Does Right Now

The app currently provides:

- uploaded video handling and metadata extraction
- preprocessing that starts immediately after upload, with playback unlocked after preview generation
- `open_vocab` daylight detection defaults and benchmarked thermal baseline presets
- `Bridge` tracking with confidence-based stale-track cutoff and optional `CSRT` comparison mode
- on-video bbox overlays, distance estimate, guidance line, and control-signal emulator
- drone profiles, camera optics profiles, and target profiles that feed the guidance math
- typed config and domain models for continued milestone work

The project is past the pure skeleton phase and is now in a presentation-ready prerecorded-video guidance stage. Export artifacts, stronger tracking semantics, and broader hardening remain backlog items after the demo.
