# Milestone 1 Spec: Skeleton and Spec Foundation

## Problem Statement

The project needs a clean, low-risk foundation before adding real video handling, detection, tracking, and export logic. The first milestone should create a structure that is easy to understand, easy to extend, and safe to validate incrementally.

## Scope

- Create the repository structure for UI, pipeline, domain, services, utilities, tests, docs, and outputs.
- Add a minimal Streamlit app shell.
- Define typed config and domain models.
- Add placeholder pipeline modules for future video IO, detection, tracking, guidance, rendering, and orchestration.
- Provide setup and workflow documentation.
- Add basic automated tests for deterministic logic.

## Inputs

- Project description for the diploma MVP
- Agreed stack: Streamlit, Python, OpenCV, Ultralytics YOLO, pytest
- Current milestone goal: foundation only

## Outputs

- Runnable repository skeleton
- Streamlit shell that opens and shows the project state
- Shared repo-level configuration file
- Milestone roadmap and initial architecture notes
- Passing basic tests for deterministic components

## Assumptions

- The current stage prioritizes readability and structure over full functionality.
- Real model inference is not required in this milestone.
- Placeholder logic is acceptable if it is clearly marked as placeholder behavior.
- Repo-relative paths should be used everywhere to keep the project portable between macOS and Windows.

## Acceptance Criteria

- The repository is initialized and organized according to the intended structure.
- `app/app.py` exists and is ready to be launched with Streamlit.
- Typed data models exist for the main domain concepts.
- Placeholder modules exist for the main pipeline layers.
- The README explains setup and milestone-based workflow.
- Automated tests cover at least config validation, frame iteration, guidance math, and basic orchestration flow.

## Test Cases

1. Launch the Streamlit app and confirm the shell renders without requiring a real detector.
2. Change the sidebar config values and confirm they remain valid.
3. Run the unit tests and confirm deterministic helpers behave as expected.
4. Run the integration test and confirm placeholder orchestration produces a detection, approval, tracking, and guidance preview.

## Non-goals

- Real video upload handling
- Metadata extraction from uploaded files
- Real YOLO inference
- Real tracker integration
- Annotated video export
- Structured log export

## Open Questions

- Which pretrained detection model should be used first in Milestone 4?
- What default camera FOV assumptions should be used for angle approximation?
- Should Milestone 2 prioritize UI preview polish or backend metadata correctness?

## Implementation Notes

- Use dataclasses for domain models to keep the code explicit and learner-friendly.
- Keep placeholder behavior deterministic so tests stay fast and reliable.
- Store shared repo details in `pyproject.toml` and avoid machine-specific paths.
- Keep the Streamlit UI separate from CV pipeline logic.

## Expected Workflow

1. Validate the repository structure and docs.
2. Confirm the app shell launches.
3. Move to Milestone 2 only after the foundation is accepted.
4. Create a new short spec for the next milestone before implementing it.
