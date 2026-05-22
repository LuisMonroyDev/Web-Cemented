# 03 — Conventions

The boring stuff. Decide once, never re-debate.

## Repo top-level (after build starts)

```
Web-Cemented/
├── README.md
├── .gitignore
├── docs/                 all planning + future ADRs
├── frontend/             React app (Vite-based, see below)
└── backend/              Django project
```

`frontend` and `backend` are siblings, NOT nested. They deploy separately.

## Frontend conventions

### Tooling
- **Build tool:** Vite. (Create React App is deprecated; Next is overkill for
  a SPA we explicitly chose to keep standalone.)
- **Package manager:** npm. Don't introduce yarn/pnpm without reason.
- **Language:** Plain JS for v1. TypeScript is a great future addition but
  adds learning load on top of React; defer to v2.

### Folder structure inside `frontend/src/`
```
src/
├── main.jsx                   entry
├── App.jsx                    top-level layout
├── components/                reusable, dumb-ish UI pieces
│   ├── MerchCard.jsx
│   ├── MusicPlayer.jsx
│   └── ...
├── sections/                  landing-page sections (one per scroll block)
│   ├── HeroSection.jsx
│   ├── MusicSection.jsx
│   └── MerchSection.jsx
├── pages/                     only if/when multi-page emerges (cart, checkout-success)
├── lib/
│   ├── api.js                 all fetch calls to the backend, in one place
│   └── cart.js                cart state management
└── styles/
```

### Naming
- Components: `PascalCase.jsx`
- Hooks: `useCamelCase.js`
- Utilities: `camelCase.js`
- CSS Modules (if used): `Component.module.css`

### State management
- React's built-in `useState` and `useContext` for v1
- Cart state lives in `localStorage`, hydrated into a React context on app load
- **Do not add Redux, Zustand, Jotai, etc. in v1.** A merch site does not need
  it. Add only if you hit a problem these solve.

### Styling
TBD when first component is built. Acceptable choices, in order of preference:
1. CSS Modules (Vite supports out of the box, scoped, no extra dep)
2. Tailwind (very common, but adds learning load)
3. Plain CSS files with BEM naming

Decide before the first component, then never re-decide.

## Backend conventions

### Project layout
```
backend/
├── manage.py
├── requirements.txt
├── .env.example               committed, real .env is gitignored
├── config/                    Django "project" (settings, root urls)
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py
│   └── wsgi.py
└── apps/                      Django "apps" — feature-aligned
    ├── catalog/               Product, ProductVariant, ProductImage
    ├── orders/                Order, OrderLineItem, checkout, webhooks
    └── core/                  shared utilities, base models
```

### Why split settings/
Different config for dev vs prod (DEBUG, database URL, allowed hosts, CORS
origins) without environment-variable acrobatics. `base.py` has everything
shared; `dev.py` and `prod.py` import from it and override.

### Naming
- Models: singular `PascalCase` (`Product`, not `Products`)
- Database tables: Django auto-generates from app + model name; don't override
- API endpoints: kebab-case URL paths, plural nouns
  (`/api/products`, `/api/checkout-session`)
- Python files/modules: `snake_case.py`

### URL structure
All API endpoints under `/api/`:

```
GET    /api/products              ← list active products with variants
GET    /api/products/<slug>       ← single product detail
POST   /api/checkout-session      ← create a Stripe Checkout session
POST   /api/webhooks/stripe       ← receive Stripe webhooks
```

Admin lives at `/admin/` (Django default). Public site is on a separate domain
entirely (Vercel), so the Django host effectively only serves `/api/` and
`/admin/`.

### Migrations
- Always commit migration files
- One migration = one logical change
- Never edit an applied migration; create a new one to fix it
- Run `makemigrations` then `migrate` locally before pushing

## Git conventions

### Branching
- `main` is always deployable
- Feature branches: `feature/<short-name>` (e.g., `feature/checkout-flow`)
- One feature chat → one feature branch → one PR (even if you're the only
  reviewer; the PR diff is the artifact)

### Commits
- Imperative mood: "Add product list endpoint", not "Added"
- Reference the feature file when relevant: "Implement checkout per features/03-checkout.md"
- Atomic where possible (one logical change per commit)

### What not to commit
- `.env` files (use `.env.example` instead)
- `db.sqlite3` or any local database files
- `node_modules/` or Python `__pycache__/`
- Vite/Django build output
- Anything matching `.gitignore`

## Environment variables

### Backend (.env.example will live in `backend/`)
```
DJANGO_SECRET_KEY=
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=
DATABASE_URL=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PUBLISHABLE_KEY=         # passed to frontend at build
FRONTEND_ORIGIN=                # for CORS allowlist
EMAIL_API_KEY=                  # Resend or SendGrid
BAND_NOTIFICATION_EMAIL=        # where new-order emails go
```

### Frontend (.env.example will live in `frontend/`)
```
VITE_API_BASE_URL=
VITE_STRIPE_PUBLISHABLE_KEY=
```

Vite requires the `VITE_` prefix to expose vars to client code. Anything
without that prefix is build-time only and not embedded in the bundle.

## Code review with yourself

Before merging a feature branch:
1. Run the app locally end-to-end (don't trust unit tests alone)
2. Re-read the diff in the PR view (catches sloppy commits)
3. Check for committed secrets, debug prints, `console.log` calls
4. Verify the feature file's "definition of done" is met

This is the discipline that keeps a solo project from accumulating cruft.
