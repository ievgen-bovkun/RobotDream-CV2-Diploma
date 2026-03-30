# ADR 0001: Milestone 1 Foundation Shape

## Decision

Use a package-oriented Python layout under `app/` with separate folders for UI, pipeline, domain, services, and utilities.

## Rationale

- It keeps Streamlit concerns separate from CV pipeline logic.
- It makes milestone-based growth easier without large rewrites.
- It maps directly to the diploma presentation narrative.
- It supports future reuse of the pipeline outside the Streamlit UI.

## Consequences

- The initial app stays intentionally simple.
- Some placeholder modules exist before they have full implementations.
- Real functionality can be added gradually while preserving stable interfaces.
