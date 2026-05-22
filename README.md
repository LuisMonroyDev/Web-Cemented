# Web-Cemented

Single-page band website with merch store. Built as a learning-first full-stack project.

## Stack

- **Frontend:** React, deployed on Vercel
- **Backend:** Django + Django REST Framework, deployed on Railway or Render
- **Database:** PostgreSQL (managed by backend host)
- **Payments:** Stripe Checkout (hosted)
- **Email:** Transactional service (Resend or SendGrid — TBD)

## Repo layout

```
Web-Cemented/
├── README.md              ← you are here
├── .gitignore
├── docs/
│   └── plan/
│       ├── 00-overview.md       ← what we're building, for whom
│       ├── 01-architecture.md   ← how the pieces fit
│       ├── 02-performance.md    ← budgets, hot paths, traps to avoid
│       ├── 03-conventions.md    ← folder layout, naming, the boring stuff
│       └── features/
│           ├── _TEMPLATE.md     ← copy this when planning a new feature
│           └── (one file per feature, added as we go)
└── (frontend/ and backend/ directories added when we start building)
```

## How to use these docs

Each `feature` chat picks up a single feature file from `docs/plan/features/`
and builds it. The feature file should contain everything that chat needs to
execute without re-litigating decisions made in the plan chat.

If a feature chat finds itself making an architectural decision, stop —
that decision belongs in `01-architecture.md`, updated from the plan chat.

## Status

Pre-build. Planning phase. No application code yet.
