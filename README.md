# Drone Detection, Approval, Tracking, and Guidance Demo

This repository contains the Milestone 1 foundation for a diploma-project MVP built with Streamlit and a modular computer-vision pipeline. The current goal is to keep the codebase clean, portable, and ready for small validated iterations.

## Current Status

- Milestone: `Milestone 1 - Skeleton and Spec Foundation`
- Scope: project structure, app shell, typed models, placeholder pipeline modules, docs, and test scaffolding
- Real video ingestion, detection, and tracking are intentionally deferred to later milestones

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
python3 -m venv .venv
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
- placeholder orchestration flow

## Milestone Workflow

For each milestone:

1. Write or update the spec in [`docs/specs/`](docs/specs/).
2. Implement the smallest working slice.
3. Validate manually in the Streamlit app.
4. Add or update automated tests.
5. Record important decisions and limitations in docs.

## What the App Does Right Now

The app currently provides:

- a Streamlit shell with operator controls
- typed config and domain models
- a deterministic placeholder pipeline preview
- a visible foundation for later video upload, detection, approval, and tracking work

This is intentional: the structure is ready, but the project is still in the “safe foundation” phase.
