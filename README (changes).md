# Proposed changes to README.md

> This file collects proposed edits to `README.md` for review.
> Nothing here is merged into the original yet.

## Change 1 — Repo layout block

The skeleton now exists, so the layout block can show real directories.

Replace this line:

    └── (frontend/ and backend/ directories added when we start building)

with:

    ├── frontend/             React app (Vite + React)
    └── backend/              Django + DRF API

## Change 2 — Status section

Replace:

    Pre-build. Planning phase. No application code yet.

with:

    Skeleton in place. The frontend (Vite + React) and backend (Django + DRF)
    are scaffolded and verified talking to each other through a health-check
    endpoint. Feature work is next — see docs/plan/features/.
