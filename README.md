# Drone Detection, Approval, Tracking, and Guidance Demo

This repository contains the Milestone 1 foundation for a diploma-project MVP built with Streamlit and a modular computer-vision pipeline. The current goal is to keep the codebase clean, portable, and ready for small validated iterations.

It processes prerecorded drone video to detect another drone in the field of view, confirm the target, track it, and generate simple visual guidance. The architecture is intentionally structured so the MVP can later be extended toward broader drone guidance tasks.

## Current Status

- Primary completed milestones:
  - `Milestone 1` foundation and typed contracts
  - `Milestone 2` uploaded video handling and metadata extraction
  - `Milestone 3` frame iteration and runtime chunk processing
  - `Milestone 4` real detector integration and daylight benchmarking
- Current in-progress work:
  - `Milestone 6` bridge tracking and detector-refresh tuning
  - `Milestone 7` guidance overlays and runtime synchronization
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

For stable local behavior, use Python `3.11`. The repository pins this via [.python-version](/Users/i.bovkun/PycharmProjects/DroneTracking/.python-version) and [pyproject.toml](/Users/i.bovkun/PycharmProjects/DroneTracking/pyproject.toml). Avoid Python `3.14` for this project because it has already caused environment mismatches with detection dependencies.

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
- a Streamlit runtime UI with detection settings and progress state
- incremental daytime YOLO detection with bridge tracking between detector refreshes
- on-video bbox overlays, runtime counters, and pipeline preview cards
- typed config and domain models for continued milestone work

The project is past the pure skeleton phase and is now in a working daytime-baseline stage. Manual approval, export artifacts, stronger tracking, and thermal-specific tuning are still ahead.
