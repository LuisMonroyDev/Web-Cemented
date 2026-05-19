# 02 — Performance

## The honest framing

For a band site with low traffic, "performance" is mostly about not doing
anything stupid. The site won't be slow because of optimization choices — it
will be slow because of a small number of well-known anti-patterns. This doc
names those traps so we avoid them, and sets budgets so we know what "fast
enough" means.

## Budgets (v1 targets)

These are targets, not hard requirements. If we're over, investigate; if we're
way over, fix.

| Metric | Target | Why |
|---|---|---|
| Time to first contentful paint (home page) | < 1.5s on 4G | If music doesn't play within 2s, fans bounce |
| Largest contentful paint | < 2.5s on 4G | Core Web Vitals threshold for "good" |
| Total JS bundle (gzipped) | < 200KB | Above this, mobile load times suffer noticeably |
| Largest image on page | < 200KB | Force WebP/AVIF + responsive sizing |
| API response time (product list) | < 200ms p95 | Below human perception threshold |
| API response time (checkout creation) | < 500ms p95 | One Stripe round-trip, acceptable wait |
| Lighthouse performance score | ≥ 85 mobile | Industry "good" threshold |

These come from common web performance guidance (Core Web Vitals, RAIL model).
The specific numbers are reasonable defaults — not gospel. Adjust if measurement
shows real users care about something different.

## The 20% that delivers 80% of the perf

In order of impact, the traps to actively avoid:

### 1. N+1 database queries (highest impact for the backend)
**The trap:** Fetching a list of products, then for each one fetching its
variants in a separate query. 1 query becomes 1+N queries.

**The fix:** Django's `select_related()` (for foreign keys) and
`prefetch_related()` (for reverse relations and many-to-many). Use them on
any view that returns a list.

**Verification:** Use Django Debug Toolbar in development. Any list view firing
more than ~3 queries is suspect. The product-list endpoint should fire **1 or 2
queries total**, regardless of product count.

### 2. Oversized images (highest impact for the frontend)
**The trap:** Uploading a 4MB photo from a phone and using it as the merch
thumbnail. Mobile users on cellular pay for every byte.

**The fix:**
- Pre-process images on upload: store multiple sizes (thumbnail, medium, full)
- Serve WebP or AVIF with JPEG fallback
- Use `<img srcset>` for responsive selection
- Lazy-load images below the fold (`loading="lazy"`)

### 3. Render-blocking JavaScript
**The trap:** Loading the entire React app before showing any content.

**The fix:** For v1, accept some delay — this is a SPA, not server-rendered.
Mitigations: code-split the merch section if the bundle grows, lazy-load the
music player if it's heavy. Don't over-engineer this until the bundle is
actually big.

### 4. Unindexed database lookups
**The trap:** Querying orders by email without an index on the email column.
Initially fast, gets slow as orders grow.

**The fix:** Index every column you query/filter/join on. Django: `db_index=True`
on the field, or `class Meta: indexes = [...]`. Migration runs in seconds.

**Especially:** `Order.email`, `Order.stripe_session_id`, `ProductVariant.sku`,
any `slug` field used in URLs.

### 5. No caching for static-ish data
**The trap:** Hitting the database to render the product list on every single
page load, when products change once a week.

**The fix for v1:** HTTP cache headers on the product-list endpoint
(`Cache-Control: public, max-age=60`). 60 seconds of staleness is fine; it
saves 99% of the database hits on a popular page.

Do NOT add Redis. Do NOT add a cache layer. HTTP caching is enough for v1.

### 6. Synchronous email sending in webhook handlers
**The trap:** Stripe webhook handler sends 2 emails synchronously; if the
email service is slow, the webhook times out, Stripe retries, you get
duplicate orders.

**The fix:** Either (a) send emails after returning 200 to Stripe (Django
`transaction.on_commit()` is your friend), or (b) make the email service
call have a tight timeout and don't let it block the webhook response.

## What we are NOT optimizing for in v1

- **Concurrent user load.** Realistic traffic for a band site is dozens of
  visitors a day, not thousands per second. Optimizing for scale we don't
  have is the textbook waste of time.
- **Sub-100ms response times.** Anything under 300ms feels instant. Chasing
  100ms requires effort that should go elsewhere.
- **Offline support / PWA.** Not relevant for a merch store. People are buying,
  not reading.
- **Server-side rendering.** A SPA renders client-side. For a single page with
  no SEO requirements beyond the homepage, this is fine. (If SEO becomes
  important later, that's when SSR or static generation becomes worth the
  complexity.)

## Measurement

Before optimizing anything, measure. The honest workflow:

1. Build the feature simply
2. Measure with real tools (Lighthouse, Django Debug Toolbar, browser DevTools
   Network tab)
3. Compare to budget
4. Optimize only what's actually over budget

"Premature optimization is the root of all evil" — Knuth. He was right. The
above traps are exceptions because they're cheap to avoid and expensive to
fix later. Everything else: measure first.
