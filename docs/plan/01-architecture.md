# 01 — Architecture

## Shape

Decoupled architecture:

```
┌────────────────┐         HTTPS / JSON         ┌─────────────────┐
│  React (SPA)   │ ───────────────────────────▶ │  Django + DRF   │
│   on Vercel    │ ◀─────────────────────────── │  on Railway/    │
│                │                              │  Render         │
└────────────────┘                              └────────┬────────┘
                                                         │
                                                         ▼
                                                 ┌───────────────┐
                                                 │  PostgreSQL   │
                                                 │  (managed)    │
                                                 └───────────────┘

        ┌─────────────┐                          ┌───────────────┐
        │   Stripe    │ ◀─── redirect ───────────│  Stripe       │
        │  Checkout   │                          │  webhook ────▶│  (back to backend)
        └─────────────┘                          └───────────────┘
```

## Key decisions and why

| Decision | Choice | Why |
|---|---|---|
| Frontend framework | React (standalone, not Next.js) | Most transferable skill. Standalone forces you to learn the client/server boundary explicitly. |
| Backend framework | Django + Django REST Framework | Free admin panel = ~2 weeks of saved CRUD work. Batteries-included = less integration fatigue. |
| Database | PostgreSQL | Orders, inventory, line items are inherently relational. Industry standard. Transfers everywhere. |
| Payments | Stripe Checkout (hosted page) | PCI compliance is Stripe's problem. Redirect-based, simpler webhook story than embedded Elements. |
| Customer auth | None (guest checkout) | One less subsystem. Email is the order identity. Accounts are an exit-ramp, not v1. |
| Admin auth | Django built-in | Free with the framework. Strong defaults. |
| Frontend hosting | Vercel | Easiest React deploy in existence. Free tier covers this project indefinitely. |
| Backend hosting | Railway or Render | Both bundle Postgres. Both are "git push, get a URL." Pick whichever is cheaper at deploy time. |
| Email | Resend or SendGrid | Decide when implementing order-confirmation feature. Resend is simpler if no constraints. |

## Cross-cutting concerns the architecture must handle

### CORS (Cross-Origin Resource Sharing)
React on `*.vercel.app` (or a custom domain) calls Django on `*.railway.app`
(or similar). Browsers block this by default. Django must be configured with
`django-cors-headers` to allow the frontend's origin. **This is the #1 source
of "why isn't this working" issues for this stack. Solve it once, document it,
move on.**

### CSRF
For a JSON API consumed by a SPA, the traditional Django CSRF flow doesn't
apply cleanly. Two acceptable patterns:
- Use session auth + CSRF token endpoint (Django default, requires extra setup
  for SPAs)
- Use token/JWT auth and disable CSRF on API endpoints

For v1, since there's no customer auth, this primarily concerns the admin —
which uses Django's built-in admin auth and CSRF, untouched. **The public
API endpoints (product listing, checkout creation) don't need user-bound CSRF
because there's no authenticated user session to forge from.** They do need
rate limiting and origin validation — see Security section below.

### Stripe webhooks
Payment confirmation is **async**. The flow:
1. Frontend asks backend to create a Stripe Checkout Session
2. Backend creates the session, returns the URL
3. Browser redirects to Stripe, customer pays
4. Stripe redirects browser to a "success" URL on the frontend
5. **Separately**, Stripe POSTs a webhook to the backend confirming payment
6. Backend's webhook handler creates the order, decrements stock, sends emails

The "success" URL alone is not trustworthy — a user could fake hitting it.
The webhook is the source of truth. Webhook handler must be **idempotent**
(Stripe retries on failure; the same payment may arrive twice).

### Inventory race conditions
Two customers buy the last shirt at the same time. The naive flow
("check stock → create order → decrement stock") has a race window.

For v1 with realistic traffic (handful of orders per day), the risk is small
but real. Mitigation: when the webhook creates the order, wrap the stock
decrement in a database transaction using `select_for_update()` to lock the
row. If stock would go negative, mark the order for refund instead of fulfilling.

This is a known limitation we're accepting for v1. Document the trade-off in
the feature file for order processing.

## Data model (v1, sketch — finalize in the product feature file)

- **Product** — name, description, base price, active flag, slug
- **ProductVariant** — belongs to Product. Has SKU, size, color, price (can
  override product price), stock_count
- **ProductImage** — belongs to Product (or Variant for variant-specific images)
- **Order** — email, shipping address fields, total, Stripe session ID, status
  (`pending` / `paid` / `shipped` / `refunded`), created_at
- **OrderLineItem** — belongs to Order and ProductVariant. quantity,
  price_at_purchase (snapshot — never reference the product price later)

`price_at_purchase` is non-negotiable. If you change a shirt's price next
month, last month's orders must still reflect what was actually charged.

## What v1 explicitly does NOT have

- Caching layer (Redis, Memcached). Postgres handles this volume directly.
- Background job queue (Celery, RQ). Stripe webhooks are the only async work
  and they're event-driven, not scheduled.
- CDN beyond what Vercel provides for the frontend by default.
- Containerization (Docker). Railway/Render handle deployment from git directly.

Each of the above is a defensible v2 addition if the project grows. None
should be built in v1 "just in case."

## Security posture for v1

Since the priority docs are architecture and performance (not security), this
section is brief — but cannot be empty for an app that takes money.

- **No raw card data ever touches our servers** — Stripe Checkout handles it
- **Secrets in environment variables**, never committed (`.gitignore` enforces)
- **HTTPS everywhere** (handled by Vercel and Railway/Render by default)
- **Rate limiting on public endpoints** (especially checkout session creation
  — otherwise an attacker can spam Stripe API calls on our dime). Django
  Ratelimit is a one-line decorator.
- **Webhook signature verification** for Stripe webhooks (Stripe signs every
  webhook; reject any with bad signatures)
- **Admin behind strong password + MFA** (you, as the band's admin)
- **CORS restricted** to known frontend origins; not `*`
- **SQL injection** is not a meaningful risk because we're using Django's ORM,
  not raw SQL — but never construct queries via string formatting

A full threat model is out of scope for v1 docs. If the project grows or
starts handling more sensitive data, add `04-security.md`.
